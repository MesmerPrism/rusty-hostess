"""Projected Motion Breath broker bridge helpers for Hostess CLI flows."""

from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Any

from tools.hostessctl.broker_transport import (
    BrokerWebSocketClient,
    accept_broker_stream_event,
)
from tools.hostessctl.pmb_evidence import (
    PMB_BREATH_FEEDBACK_STATE_STREAM,
    PMB_BREATH_SELECTION_STATE_STREAM,
    PMB_BREATH_STATE_STREAM,
    PMB_BREATH_STATE_VALUE_STREAM,
    PMB_BREATH_VOLUME_CONTROLLER_STREAM,
    PMB_BREATH_VOLUME_POLAR_STREAM,
    PMB_BREATH_VOLUME_SELECTED_STREAM,
    PMB_BREATH_VOLUME_STREAM,
)


def publish_pmb_feedback_samples(
    args: argparse.Namespace,
    route_report: dict[str, Any],
    send_broker_command: Any,
) -> dict[str, Any]:
    limit = max(0, int(getattr(args, "pmb_feedback_publish_limit", 0)))
    breath_samples = select_pmb_output_samples(route_report.get("breath_samples", []), limit)
    selected_source_preference = str(getattr(args, "pmb_breath_selected_source", "auto") or "auto")
    selected_breath_samples, selected_source_effective = select_pmb_selected_breath_samples(
        breath_samples,
        selected_source_preference,
        limit,
    )
    state_samples = select_pmb_output_samples(route_report.get("state_samples", []), limit)
    state_value_samples = select_pmb_output_samples(route_report.get("state_value_samples", []), limit)
    feedback_samples = select_pmb_output_samples(route_report.get("feedback_samples", []), limit)
    breath_results: list[dict[str, Any]] = []
    for index, sample in enumerate(breath_samples):
        sequence_id = int(sample.get("sequence_id") or index + 1)
        breath_results.append(
            publish_pmb_stream_sample(
                send_broker_command,
                stream_id=PMB_BREATH_VOLUME_STREAM,
                sequence_id=sequence_id,
                payload=pmb_breath_payload(sample, sequence_id, PMB_BREATH_VOLUME_STREAM),
            )
        )
        source_stream_id = pmb_breath_source_stream_id(sample)
        if source_stream_id is not None:
            breath_results.append(
                publish_pmb_stream_sample(
                    send_broker_command,
                    stream_id=source_stream_id,
                    sequence_id=sequence_id,
                    payload=pmb_breath_payload(sample, sequence_id, source_stream_id),
                )
            )
    selected_breath_results = [
        publish_pmb_stream_sample(
            send_broker_command,
            stream_id=PMB_BREATH_VOLUME_SELECTED_STREAM,
            sequence_id=int(sample.get("sequence_id") or index + 1),
            payload=pmb_breath_payload(
                sample,
                int(sample.get("sequence_id") or index + 1),
                PMB_BREATH_VOLUME_SELECTED_STREAM,
                selected=True,
                selected_source_preference=selected_source_preference,
                selected_source_effective=selected_source_effective,
            ),
        )
        for index, sample in enumerate(selected_breath_samples)
    ]
    breath_results.extend(selected_breath_results)
    selection_state_results: list[dict[str, Any]] = []
    if limit > 0:
        selection_state_results.append(
            publish_pmb_stream_sample(
                send_broker_command,
                stream_id=PMB_BREATH_SELECTION_STATE_STREAM,
                sequence_id=1,
                payload={
                    "schema": "rusty.manifold.breath.selection_state.v1",
                    "stream_id": PMB_BREATH_SELECTION_STATE_STREAM,
                    "sequence_id": 1,
                    "selected_stream_id": PMB_BREATH_VOLUME_SELECTED_STREAM,
                    "selected_source_preference": selected_source_preference,
                    "selected_source_effective": selected_source_effective,
                    "source_stream_ids": [
                        PMB_BREATH_VOLUME_POLAR_STREAM,
                        PMB_BREATH_VOLUME_CONTROLLER_STREAM,
                    ],
                    "selected_sample_count": len(selected_breath_samples),
                    "publisher": "hostessctl.record_values",
                },
            )
        )
    breath_results.extend(selection_state_results)
    state_results = [
        publish_pmb_stream_sample(
            send_broker_command,
            stream_id=PMB_BREATH_STATE_STREAM,
            sequence_id=int(sample.get("sequence_id") or index + 1),
            payload=pmb_breath_state_payload(
                sample,
                int(sample.get("sequence_id") or index + 1),
            ),
        )
        for index, sample in enumerate(state_samples)
    ]
    state_value_results = [
        publish_pmb_stream_sample(
            send_broker_command,
            stream_id=PMB_BREATH_STATE_VALUE_STREAM,
            sequence_id=int(sample.get("sequence_id") or index + 1),
            payload=pmb_breath_state_value_payload(
                sample,
                int(sample.get("sequence_id") or index + 1),
            ),
        )
        for index, sample in enumerate(state_value_samples)
    ]
    feedback_results = [
        publish_pmb_stream_sample(
            send_broker_command,
            stream_id=PMB_BREATH_FEEDBACK_STATE_STREAM,
            sequence_id=int(sample.get("sequence_id") or index + 1),
            payload={
                "schema": "rusty.manifold.breath.feedback_state.v1",
                "stream_id": PMB_BREATH_FEEDBACK_STATE_STREAM,
                "sequence_id": int(sample.get("sequence_id") or index + 1),
                "source_breath_sequence_id": sample.get("source_breath_sequence_id"),
                "source_id": sample.get("source_id"),
                "sample_time_unix_ns": sample.get("sample_time_unix_ns"),
                "volume01": sample.get("volume01"),
                "phase": sample.get("phase"),
                "quality": sample.get("quality"),
                "processor_id": "processor.projected_motion_breath.live_bridge",
                "publisher": "hostessctl.record_values",
            },
        )
        for index, sample in enumerate(feedback_samples)
    ]
    return {
        "limit": limit,
        "selected_source_preference": selected_source_preference,
        "selected_source_effective": selected_source_effective,
        "breath_requested_count": len(route_report.get("breath_samples", [])),
        "state_requested_count": len(route_report.get("state_samples", [])),
        "state_value_requested_count": len(route_report.get("state_value_samples", [])),
        "feedback_requested_count": len(route_report.get("feedback_samples", [])),
        "breath_published_count": sum(
            1
            for result in breath_results
            if result.get("stream_id") == PMB_BREATH_VOLUME_STREAM and result.get("status") == "pass"
        ),
        "selected_breath_published_count": sum(
            1
            for result in selected_breath_results
            if result.get("status") == "pass"
        ),
        "selection_state_published_count": sum(
            1
            for result in selection_state_results
            if result.get("status") == "pass"
        ),
        "state_published_count": sum(1 for result in state_results if result.get("status") == "pass"),
        "state_value_published_count": sum(
            1 for result in state_value_results if result.get("status") == "pass"
        ),
        "feedback_published_count": sum(1 for result in feedback_results if result.get("status") == "pass"),
        "published_count": sum(
            1
            for result in breath_results + state_results + state_value_results + feedback_results
            if result.get("status") == "pass"
        ),
        "published": any(
            result.get("status") == "pass"
            for result in breath_results + state_results + state_value_results + feedback_results
        ),
        "breath_results": breath_results,
        "selected_breath_results": selected_breath_results,
        "state_results": state_results,
        "state_value_results": state_value_results,
        "feedback_results": feedback_results,
    }


def pmb_breath_payload(
    sample: dict[str, Any],
    sequence_id: int,
    stream_id: str,
    *,
    selected: bool = False,
    selected_source_preference: str = "auto",
    selected_source_effective: str = "auto",
) -> dict[str, Any]:
    payload = {
        "schema": "rusty.manifold.breath.volume.v1",
        "stream_id": stream_id,
        "sequence_id": sequence_id,
        "source_id": sample.get("source_id"),
        "source_kind": pmb_breath_source_kind(sample),
        "input_stream_id": sample.get("input_stream_id"),
        "normalized_stream_id": sample.get("normalized_stream_id"),
        "sample_time_unix_ns": sample_time_unix_ns_from_sample(sample),
        "volume01": sample.get("volume01"),
        "phase": sample.get("phase"),
        "quality": sample.get("quality"),
        "quality01": sample.get("quality01", sample.get("tracking01", 1.0)),
        "tracking01": sample.get("tracking01"),
        "processor_id": "processor.projected_motion_breath.live_bridge",
        "publisher": "hostessctl.record_values",
    }
    if selected:
        payload.update(
            {
                "selected": True,
                "selected_source_preference": selected_source_preference,
                "selected_source_effective": selected_source_effective,
            }
        )
    return payload


def pmb_breath_state_payload(sample: dict[str, Any], sequence_id: int) -> dict[str, Any]:
    state = str(sample.get("state") or sample.get("phase") or "pause")
    return {
        "schema": "rusty.manifold.breath.state.v1",
        "stream_id": PMB_BREATH_STATE_STREAM,
        "sequence_id": sequence_id,
        "source_breath_sequence_id": sample.get("source_breath_sequence_id"),
        "source_id": sample.get("source_id"),
        "sample_time_unix_ns": sample_time_unix_ns_from_sample(sample),
        "state": state,
        "phase": state,
        "state01": sample.get("state01"),
        "tracking01": sample.get("tracking01"),
        "quality": sample.get("quality"),
        "processor_id": "processor.projected_motion_breath.live_bridge",
        "publisher": "hostessctl.record_values",
    }


def pmb_breath_state_value_payload(sample: dict[str, Any], sequence_id: int) -> dict[str, Any]:
    value01 = sample.get("value01")
    state = str(sample.get("state") or sample.get("phase") or "pause")
    return {
        "schema": "rusty.manifold.breath.state_value.v1",
        "stream_id": PMB_BREATH_STATE_VALUE_STREAM,
        "sequence_id": sequence_id,
        "source_breath_sequence_id": sample.get("source_breath_sequence_id"),
        "source_state_sequence_id": sample.get("source_state_sequence_id"),
        "source_id": sample.get("source_id"),
        "sample_time_unix_ns": sample_time_unix_ns_from_sample(sample),
        "state": state,
        "phase": state,
        "state01": sample.get("state01"),
        "target01": sample.get("target01"),
        "value01": value01,
        "volume01": value01,
        "delta_seconds": sample.get("delta_seconds"),
        "stale_gap": sample.get("stale_gap"),
        "tracking01": sample.get("tracking01"),
        "quality": sample.get("quality"),
        "processor_id": "processor.projected_motion_breath.state_value",
        "publisher": "hostessctl.record_values",
    }


def pmb_breath_source_kind(sample: dict[str, Any]) -> str:
    text = " ".join(
        str(sample.get(key) or "")
        for key in ("source_id", "input_stream_id", "normalized_stream_id")
    ).lower()
    if "polar" in text or "bio:polar" in text:
        return "polar"
    if "controller" in text or "object_pose" in text or "motion.object" in text:
        return "controller"
    return "unknown"


def pmb_breath_source_stream_id(sample: dict[str, Any]) -> str | None:
    source_kind = pmb_breath_source_kind(sample)
    if source_kind == "polar":
        return PMB_BREATH_VOLUME_POLAR_STREAM
    if source_kind == "controller":
        return PMB_BREATH_VOLUME_CONTROLLER_STREAM
    return None


def select_pmb_selected_breath_samples(
    breath_samples: list[dict[str, Any]],
    selected_source_preference: str,
    limit: int,
) -> tuple[list[dict[str, Any]], str]:
    if limit <= 0:
        return [], selected_source_preference
    source_kinds = [pmb_breath_source_kind(sample) for sample in breath_samples]
    effective = selected_source_preference
    if selected_source_preference == "auto":
        if "polar" in source_kinds:
            effective = "polar"
        elif "controller" in source_kinds:
            effective = "controller"
        else:
            effective = "unknown"
    selected = [
        sample
        for sample in breath_samples
        if effective == "unknown" or pmb_breath_source_kind(sample) == effective
    ]
    return selected[:limit], effective


def select_pmb_output_samples(raw_samples: Any, limit: int) -> list[dict[str, Any]]:
    if limit <= 0 or not isinstance(raw_samples, list):
        return []
    by_source: dict[str, list[dict[str, Any]]] = {}
    source_order: list[str] = []
    for sample in raw_samples:
        if not isinstance(sample, dict):
            continue
        source_id = str(sample.get("source_id") or "source.unknown")
        if source_id not in by_source:
            by_source[source_id] = []
            source_order.append(source_id)
        by_source[source_id].append(sample)
    selected: list[dict[str, Any]] = []
    cursor = 0
    while len(selected) < limit and source_order:
        progressed = False
        for source_id in source_order:
            source_samples = by_source[source_id]
            if cursor < len(source_samples):
                selected.append(source_samples[cursor])
                progressed = True
                if len(selected) >= limit:
                    break
        if not progressed:
            break
        cursor += 1
    return selected


def publish_pmb_stream_sample(
    send_broker_command: Any,
    *,
    stream_id: str,
    sequence_id: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    ack = send_broker_command(
        "publish_stream_event",
        {
            "stream": stream_id,
            "sequence_id": sequence_id,
            "payload": payload,
        },
    )
    return {
        "stream_id": stream_id,
        "sequence_id": sequence_id,
        "status": ack.get("status"),
        "request_id": ack.get("request_id"),
    }


def sample_time_unix_ns_from_sample(sample: dict[str, Any]) -> int:
    value = sample.get("sample_time_unix_ns")
    if isinstance(value, (int, float)):
        return int(value)
    sample_time_s = sample.get("sample_time_s")
    if isinstance(sample_time_s, (int, float)):
        return int(max(0.0, float(sample_time_s)) * 1_000_000_000)
    return 0


def listen_for_pmb_receipts(
    args: argparse.Namespace,
    ws: BrokerWebSocketClient,
    stream_rows: dict[str, dict[str, Any]],
    events_jsonl: Path,
    broker_acks: list[dict[str, Any]],
) -> None:
    deadline = time.monotonic() + max(0.0, float(getattr(args, "pmb_receipt_listen_seconds", 0.0)))
    with events_jsonl.open("a", encoding="utf-8") as events_file:
        while time.monotonic() < deadline:
            remaining = max(0.05, min(0.25, deadline - time.monotonic()))
            message = ws.recv_json(timeout=remaining)
            if message is None:
                continue
            if message.get("type") == "stream_event":
                accept_broker_stream_event(message, stream_rows, events_jsonl, events_file=events_file)
            else:
                broker_acks.append(
                    {
                        "command": str(message.get("command") or message.get("type") or "broker-message"),
                        "request_id": message.get("request_id"),
                        "status": "observed",
                        "reply": message,
                    }
                )
