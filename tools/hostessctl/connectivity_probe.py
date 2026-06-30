"""Quest connectivity topology probe reports for hostessctl."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tools.hostessctl.runtime import run_captured as default_run_captured
from tools.hostessctl.connectivity_bluetooth import (
    live_bluetooth_report,
    qcl051_ble_gatt_payload_checks,
    qcl050_rfcomm_payload_checks,
    live_bluetooth_status,
    bluetooth_protocol_check,
    bluetooth_bytes_exchanged,
    bluetooth_measurements,
    bluetooth_transport_for_probe,
    collect_quest_bluetooth_status,
    collect_windows_bluetooth_status,
    qcl051_payload_sessions,
    qcl051_session_android,
    qcl051_session_cleanup_pass,
    qcl051_session_protocol_pass,
    qcl051_session_windows,
    quest_bluetooth_adapter_status,
    quest_bluetooth_adapter_summary,
    run_qcl050_android_rfcomm_probe,
    run_qcl051_android_ble_gatt_probe,
    topology_for_bluetooth_probe,
    windows_bluetooth_adapter_status,
    windows_bluetooth_adapter_summary,
    windows_bluetooth_service_status,
    windows_bluetooth_service_summary,
)
from tools.hostessctl.connectivity_udp import (
    DEFAULT_QCL080_UDP_PORT,
    DEFAULT_UDP_MARKER,
    device_to_host_udp_freshness,
    latest_qcl080_app_marker,
    live_udp_freshness_report,
    qcl080_app_owned_marker_observed,
    qcl080_makepad_runtime_properties,
    runtime_qcl080_udp_sender_check_from_result,
    udp_endpoint_source,
)
from tools.hostessctl.connectivity_firewall import (
    CONNECTIVITY_FIREWALL_RULE_SCHEMA,
    DEFAULT_QCL010_TCP_ECHO_PORT,
    DEFAULT_WPF_FIREWALL_PROGRAM,
    active_windows_network_categories,
    build_windows_firewall_rule_remove_script,
    build_windows_firewall_rule_script,
    build_windows_firewall_rule_verify_script,
    collect_windows_network_profile,
    diagnostic_python_program_path,
    firewall_rule_action,
    network_profile_summary,
    normalize_firewall_program_path,
    normalize_firewall_profiles,
    normalize_firewall_protocol,
    ps_string_literal,
    run_windows_firewall_rule,
    verify_windows_firewall_rule_report,
    windows_firewall_listener_status,
    windows_firewall_listener_summary,
    windows_firewall_rule_report,
    windows_network_profile_status,
)
from tools.hostessctl.connectivity_lan import (
    live_same_wifi_report,
    adb_text,
    choose_host_ip,
    collect_device_identity,
    collect_host_ipv4_candidates,
    collect_windows_mobile_hotspot,
    default_run_captured_timeout,
    device_to_host_ping,
    device_to_host_tcp_echo,
    host_to_device_ping,
    is_ipv4,
    parse_ip_addr_output,
    ping_summary,
    same_subnet_check,
    socket_host_ipv4_candidates,
)
from tools.hostessctl.connectivity_media import (
    qcl082_fixture_body,
    qcl082_media_stream_session_body,
    qcl082_media_stream_runtime_status_body,
)
from tools.hostessctl.connectivity_media_receiver import (
    parse_rmanvid1_capture,
    qcl082_media_stream_receiver_capture_body,
)
from tools.hostessctl.connectivity_websocket import (
    live_websocket_report,
)
from tools.hostessctl.connectivity_topology import (
    DEFAULT_TOPOLOGY_FIXTURE_PROFILES,
    TOPOLOGY_PROBE_IDS,
    is_topology_fixture_profile,
    topology_for_args,
    topology_fixture_body,
    topology_for_probe,
    topology_defaults_for_owner,
    windows_mobile_hotspot_status,
    windows_mobile_hotspot_summary,
)
from tools.hostessctl.connectivity_topology_live import (
    LIVE_DIRECT_WIFI_PROBE_IDS,
    live_direct_wifi_topology_report,
)
from tools.hostessctl.connectivity_topology_lifecycle import (
    run_wifi_direct_lifecycle_template,
    wifi_direct_lifecycle_probe_report,
)
from tools.hostessctl.connectivity_probe_fixtures import (
    fixture_report,
    qcl000_fixture_body,
    qcl010_fixture_body,
    qcl010_fixture_listener_firewall,
    qcl010_fixture_network_profile,
    qcl011_fixture_body,
    qcl05x_fixture_body,
    qcl080_fixture_body,
    qcl080_fixture_listener_firewall,
    qcl081_fixture_body,
    qcl083_fixture_body,
    qcl084_fixture_body,
)
from tools.hostessctl.connectivity_probe_validation import (
    CONNECTIVITY_PROBE_SCHEMA,
    CONNECTIVITY_PROBE_VALIDATION_SCHEMA,
    VALID_PROBE_IDS,
    VALID_STATUSES,
    validate_connectivity_probe_report,
)
from tools.hostessctl.connectivity_probe_live_reports import (
    live_qcl010_status,
    live_qcl011_status,
    live_qcl080_status,
    live_qcl081_status,
    live_qcl083_status,
    live_qcl084_status,
    measurements_from_checks,
    measurements_from_lsl_probe,
    measurements_from_osc_probe,
    measurements_from_udp_check,
    measurements_from_zeromq_probe,
    protocol_topology_for_report,
    tcp_echo_listener_from_result,
    udp_listener_from_result,
)
from tools.hostessctl.connectivity_data_protocols import (
    live_lsl_report,
    live_osc_report,
    live_zeromq_report,
    zeromq_checks_from_probe,
    osc_checks_from_probe,
    lsl_checks_from_probe,
    lsl_discovery_sample_continuity,
    lsl_manifold_broker_probe,
    lsl_quest_runtime_preflight,
    osc_loopback_probe,
    run_qcl083_android_osc_probe,
    run_qcl084_android_zeromq_probe,
    zeromq_loopback_probe,
)
from tools.hostessctl.connectivity_probe_common import (
    DEFAULT_TCP_MARKER,
    append_issue_once,
    base_report,
    issue_row,
    check_status,
    check_skipped,
    check_row,
    check_passed,
    ensure_probe_run_id,
    wait_for_json_file,
    strip_powershell_clixml_noise,
    read_json_file,
    completed_observed,
    float_value,
    int_value,
    list_value,
    object_value,
    percentile,
    shell_word,
    trim_text,
)


def run_connectivity_probe(
    args: argparse.Namespace,
    *,
    run_captured_func: Any | None = None,
    run_timeout_func: Any | None = None,
    clock_func: Any | None = None,
    host_ipv4_func: Any | None = None,
    tcp_echo_func: Any | None = None,
) -> int:
    """Write a connectivity probe report and validation sidecar."""

    run_captured = run_captured_func or default_run_captured
    clock = clock_func or utc_now
    if getattr(args, "probe_id", "QCL-010") in LIVE_DIRECT_WIFI_PROBE_IDS and getattr(
        args,
        "wifi_direct_lifecycle_report",
        "",
    ):
        report = wifi_direct_lifecycle_probe_report(
            args,
            observed_at=clock(),
        )
    elif getattr(args, "mode", "fixture") == "fixture":
        report = fixture_report(args, observed_at=clock())
    elif getattr(args, "probe_id", "QCL-010") in {"QCL-050", "QCL-051"}:
        report = live_bluetooth_report(
            args,
            run_captured_func=run_captured,
            run_timeout_func=run_timeout_func or default_run_captured_timeout,
            clock_func=clock,
        )
    elif getattr(args, "probe_id", "QCL-010") == "QCL-080":
        report = live_udp_freshness_report(
            args,
            run_captured_func=run_captured,
            run_timeout_func=run_timeout_func or default_run_captured_timeout,
            clock_func=clock,
            host_ipv4_func=host_ipv4_func,
        )
    elif getattr(args, "probe_id", "QCL-010") == "QCL-081":
        report = live_lsl_report(
            args,
            run_captured_func=run_captured,
            run_timeout_func=run_timeout_func or default_run_captured_timeout,
            clock_func=clock,
            host_ipv4_func=host_ipv4_func,
        )
    elif getattr(args, "probe_id", "QCL-010") == "QCL-083":
        report = live_osc_report(
            args,
            run_captured_func=run_captured,
            clock_func=clock,
            host_ipv4_func=host_ipv4_func,
        )
    elif getattr(args, "probe_id", "QCL-010") == "QCL-084":
        report = live_zeromq_report(
            args,
            run_captured_func=run_captured,
            clock_func=clock,
            host_ipv4_func=host_ipv4_func,
        )
    elif getattr(args, "probe_id", "QCL-010") == "QCL-079":
        report = live_websocket_report(
            args,
            clock_func=clock,
        )
    elif getattr(args, "probe_id", "QCL-010") in LIVE_DIRECT_WIFI_PROBE_IDS:
        report = live_direct_wifi_topology_report(
            args,
            run_captured_func=run_captured,
            clock_func=clock,
            host_ipv4_func=host_ipv4_func,
        )
    else:
        report = live_same_wifi_report(
            args,
            run_captured_func=run_captured,
            run_timeout_func=run_timeout_func or default_run_captured_timeout,
            clock_func=clock,
            host_ipv4_func=host_ipv4_func,
            tcp_echo_func=tcp_echo_func,
        )

    validation = validate_connectivity_probe_report(report)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    validation_out = (
        Path(args.validation_out)
        if getattr(args, "validation_out", None)
        else out.with_name(f"{out.stem}.validation-report.json")
    )
    validation_out.parent.mkdir(parents=True, exist_ok=True)
    validation_out.write_text(
        json.dumps(validation, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if getattr(args, "fail_on_error", False) and validation["status"] != "pass":
        return 2
    return 0

def utc_now() -> datetime:
    return datetime.now(UTC)
