"""Native app receipt policy helpers for Projected Motion Breath routes."""

from __future__ import annotations

import re
from typing import Any

from tools.hostessctl.pmb_support import (
    PMB_BREATH_FEEDBACK_RECEIPT_STREAM,
    PMB_BREATH_STATE_STREAM,
    PMB_BREATH_STATE_VALUE_STREAM,
    PMB_STREAM_CONTRACT_AUTHORITY,
)

PMB_APP_RECEIPT_POLICY_MAKEPAD = "makepad-feedback-receipt"
PMB_APP_RECEIPT_POLICY_NATIVE_RENDERER = "native-renderer-projection-target"

PMB_NATIVE_RENDERER_RECEIPT_SCHEMA = (
    "rusty.hostess.projected_motion_breath.native_renderer_receipt_summary.v1"
)

NATIVE_RENDERER_MARKER_PREFIX = "RUSTY_QUEST_NATIVE_RENDERER"
NATIVE_RENDERER_LOGCAT_FILTER = "RQNativeRenderer:I *:S"
NATIVE_RENDERER_SCALE_SOURCE_STATE = "hostess-manifold-breath-state-ramp"
NATIVE_RENDERER_SCALE_SOURCE_STATE_VALUE = "hostess-manifold-breath-state-value"

_FIELD_RE = re.compile(r"([A-Za-z][A-Za-z0-9_]*)=([^ \r\n]+)")
_RECEIPT_ONLY_FAILED_CHECK_IDS = {
    "validation.check.pmb_physical_live_makepad_receipts",
    "hostess.check.pmb_quest_physical_live.makepad_receipts",
    "validation.check.makepad_feedback_receipts",
}
_RECEIPT_ONLY_ISSUE_MESSAGES = {
    "issue.makepad_selected_breath_receipts_missing",
    "issue.makepad_feedback_receipts_missing",
}


def pmb_app_receipt_policy_from_args(args: Any) -> str:
    policy = str(
        getattr(args, "app_receipt_policy", PMB_APP_RECEIPT_POLICY_MAKEPAD)
        or PMB_APP_RECEIPT_POLICY_MAKEPAD
    )
    if policy not in {
        PMB_APP_RECEIPT_POLICY_MAKEPAD,
        PMB_APP_RECEIPT_POLICY_NATIVE_RENDERER,
    }:
        return PMB_APP_RECEIPT_POLICY_MAKEPAD
    return policy


def pmb_app_receipt_policy(evidence: dict[str, Any]) -> str:
    execution = evidence.get("execution", {})
    policy = str(
        evidence.get("app_receipt_policy")
        or execution.get("app_receipt_policy")
        or ""
    )
    if policy in {
        PMB_APP_RECEIPT_POLICY_MAKEPAD,
        PMB_APP_RECEIPT_POLICY_NATIVE_RENDERER,
    }:
        return policy
    if isinstance(evidence.get("native_app_receipt_summary"), dict):
        return PMB_APP_RECEIPT_POLICY_NATIVE_RENDERER
    return PMB_APP_RECEIPT_POLICY_MAKEPAD


def pmb_effective_receipt_listen_seconds(args: Any) -> float:
    if pmb_app_receipt_policy_from_args(args) == PMB_APP_RECEIPT_POLICY_NATIVE_RENDERER:
        return 0.0
    return max(0.0, float(getattr(args, "receipt_listen_seconds", 0.0)))


def native_renderer_receipt_summary_from_logcat(
    log_text: str,
    *,
    broker_summary: dict[str, Any] | None = None,
    route_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    marker_fields = [
        fields
        for line in log_text.splitlines()
        if NATIVE_RENDERER_MARKER_PREFIX in line
        for fields in [_parse_marker_fields(line)]
        if _is_native_projection_target_marker(fields)
    ]
    latest = marker_fields[-1] if marker_fields else {}
    broker = broker_summary or {}
    route = route_summary or {}
    expected_state_count = _int_value(broker.get("state_published_count"))
    expected_state_value_count = _int_value(broker.get("state_value_published_count"))
    expected_route_state_count = _int_value(route.get("state_sample_count"))
    expected_route_state_value_count = _int_value(route.get("state_value_sample_count"))
    expected_breath_samples = max(
        expected_state_count,
        expected_state_value_count,
        expected_route_state_count,
        expected_route_state_value_count,
    )
    breath_received_samples = _int_value(latest.get("breathReceivedSamples"))
    breath_last_sequence_id = _int_value(latest.get("breathLastSequenceId"))
    issues = _native_renderer_receipt_issues(
        latest,
        marker_count=len(marker_fields),
        breath_received_samples=breath_received_samples,
        breath_last_sequence_id=breath_last_sequence_id,
        expected_breath_samples=expected_breath_samples,
    )
    return {
        "schema": PMB_NATIVE_RENDERER_RECEIPT_SCHEMA,
        "status": "pass" if not issues else "fail",
        "app_receipt_policy": PMB_APP_RECEIPT_POLICY_NATIVE_RENDERER,
        "consumer_app": "rusty-quest-native-renderer",
        "stream_contract_authority": PMB_STREAM_CONTRACT_AUTHORITY,
        "expected_breath_state_stream": PMB_BREATH_STATE_STREAM,
        "expected_breath_value_stream": PMB_BREATH_STATE_VALUE_STREAM,
        "marker_count": len(marker_fields),
        "runtime_authority": latest.get("projectionTargetRuntimeAuthority"),
        "projection_target_pmb_available": _bool_text(
            latest.get("projectionTargetPmbAvailable")
        ),
        "projection_target_scale_driver": latest.get("projectionTargetScaleDriver"),
        "projection_target_scale_source": latest.get("projectionTargetScaleSource"),
        "breath_bridge_mode": latest.get("breathBridgeMode"),
        "breath_state_stream": latest.get("breathStateStream"),
        "breath_value_stream": latest.get("breathValueStream"),
        "breath_high_rate_json_payload": _bool_text(
            latest.get("breathHighRateJsonPayload")
        ),
        "breath_received_samples": breath_received_samples,
        "breath_last_sequence_id": breath_last_sequence_id,
        "expected_breath_samples": expected_breath_samples,
        "expected_state_published_count": expected_state_count,
        "expected_state_value_published_count": expected_state_value_count,
        "issues": issues,
    }


def pmb_app_receipt_policy_pass(evidence: dict[str, Any]) -> bool:
    policy = pmb_app_receipt_policy(evidence)
    if policy == PMB_APP_RECEIPT_POLICY_NATIVE_RENDERER:
        return pmb_native_renderer_receipt_policy_pass(evidence)
    return pmb_makepad_feedback_receipt_policy_pass(evidence)


def pmb_makepad_feedback_receipt_policy_pass(evidence: dict[str, Any]) -> bool:
    execution = evidence.get("execution", {})
    broker = evidence.get("broker_publish_summary", {})
    selected_count = _int_value(broker.get("selected_breath_published_count"))
    feedback_count = _int_value(broker.get("feedback_published_count"))
    receipt_count = _int_value(broker.get("feedback_receipt_count"))
    execution_receipt_count = _int_value(execution.get("makepad_feedback_receipt_count"))
    return (
        selected_count > 0
        and feedback_count > 0
        and receipt_count == selected_count
        and execution_receipt_count == selected_count
    )


def pmb_native_renderer_receipt_policy_pass(evidence: dict[str, Any]) -> bool:
    broker = evidence.get("broker_publish_summary", {})
    summary = evidence.get("native_app_receipt_summary", {})
    if not isinstance(summary, dict) or summary.get("status") != "pass":
        return False
    selected_count = _int_value(broker.get("selected_breath_published_count"))
    state_count = _int_value(broker.get("state_published_count"))
    state_value_count = _int_value(broker.get("state_value_published_count"))
    received_count = _int_value(summary.get("breath_received_samples"))
    last_sequence_id = _int_value(summary.get("breath_last_sequence_id"))
    return (
        broker.get("broker_transport_used") is True
        and selected_count > 0
        and state_count > 0
        and state_value_count > 0
        and received_count >= state_count
        and received_count >= state_value_count
        and last_sequence_id >= max(state_count, state_value_count)
    )


def pmb_evidence_status_accepts_receipt_policy(evidence: dict[str, Any]) -> bool:
    if evidence.get("status") == "pass":
        return True
    return (
        pmb_app_receipt_policy(evidence) == PMB_APP_RECEIPT_POLICY_NATIVE_RENDERER
        and pmb_evidence_has_receipt_only_failure(evidence)
        and pmb_native_renderer_receipt_policy_pass(evidence)
    )


def pmb_scorecard_status_accepts_receipt_policy(evidence: dict[str, Any]) -> bool:
    scorecard = evidence.get("scorecard", {})
    if isinstance(scorecard, dict) and scorecard.get("status") == "pass":
        return True
    return pmb_evidence_status_accepts_receipt_policy(evidence)


def pmb_evidence_has_receipt_only_failure(evidence: dict[str, Any]) -> bool:
    if evidence.get("status") != "fail":
        return False
    scorecard = evidence.get("scorecard", {})
    if not isinstance(scorecard, dict) or scorecard.get("status") != "fail":
        return False
    checks = scorecard.get("checks", [])
    failed_check_ids = {
        str(check.get("check_id") or "")
        for check in checks
        if isinstance(check, dict) and check.get("status") != "pass"
    }
    if not failed_check_ids:
        return False
    if not failed_check_ids.issubset(_RECEIPT_ONLY_FAILED_CHECK_IDS):
        return False
    issues = scorecard.get("issues", [])
    for issue in issues:
        if not isinstance(issue, dict):
            return False
        message = str(issue.get("message") or "")
        if message and message not in _RECEIPT_ONLY_ISSUE_MESSAGES:
            return False
    return True


def _parse_marker_fields(line: str) -> dict[str, str]:
    return {match.group(1): match.group(2) for match in _FIELD_RE.finditer(line)}


def _is_native_projection_target_marker(fields: dict[str, str]) -> bool:
    return fields.get("channel") == "projection-target" and fields.get("status") == "effective"


def _native_renderer_receipt_issues(
    fields: dict[str, str],
    *,
    marker_count: int,
    breath_received_samples: int,
    breath_last_sequence_id: int,
    expected_breath_samples: int,
) -> list[str]:
    issues: list[str] = []
    if marker_count <= 0:
        return ["issue.native_renderer_projection_target_marker_missing"]
    if fields.get("projectionTargetRuntimeAuthority") != "native-renderer":
        issues.append("issue.native_renderer_runtime_authority_missing")
    if not _bool_text(fields.get("projectionTargetPmbAvailable")):
        issues.append("issue.native_renderer_pmb_unavailable")
    if fields.get("projectionTargetScaleDriver") != "pmb":
        issues.append("issue.native_renderer_scale_driver_not_pmb")
    if fields.get("projectionTargetScaleSource") not in {
        NATIVE_RENDERER_SCALE_SOURCE_STATE,
        NATIVE_RENDERER_SCALE_SOURCE_STATE_VALUE,
    }:
        issues.append("issue.native_renderer_scale_source_not_manifold_breath")
    if fields.get("breathStateStream") != PMB_BREATH_STATE_STREAM:
        issues.append("issue.native_renderer_breath_state_stream_mismatch")
    if fields.get("breathValueStream") != PMB_BREATH_STATE_VALUE_STREAM:
        issues.append("issue.native_renderer_breath_value_stream_mismatch")
    if _bool_text(fields.get("breathHighRateJsonPayload")):
        issues.append("issue.native_renderer_breath_high_rate_json_payload")
    if breath_received_samples <= 0:
        issues.append("issue.native_renderer_breath_samples_missing")
    if breath_last_sequence_id <= 0:
        issues.append("issue.native_renderer_breath_sequence_missing")
    if expected_breath_samples > 0 and breath_received_samples < expected_breath_samples:
        issues.append("issue.native_renderer_breath_samples_below_broker_count")
    if expected_breath_samples > 0 and breath_last_sequence_id < expected_breath_samples:
        issues.append("issue.native_renderer_breath_sequence_below_broker_count")
    return issues


def _bool_text(value: Any) -> bool:
    return str(value).strip().lower() == "true"


def _int_value(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
