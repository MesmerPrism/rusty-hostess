"""Hostess T command bridge facade."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.hostessctl import android_artifacts  # noqa: E402
from tools.hostessctl import bridge_command_android_routes  # noqa: E402
from tools.hostessctl import bridge_command_live_android_routes  # noqa: E402
from tools.hostessctl import bridge_command_routes  # noqa: E402
from tools.hostessctl import bridge_route_evidence  # noqa: E402
from tools.hostessctl import broker_telemetry_routes  # noqa: E402
from tools.hostessctl import companion_catalog  # noqa: E402
from tools.hostessctl import companion_readiness  # noqa: E402
from tools.hostessctl import companion_report_projection  # noqa: E402
from tools.hostessctl import companion_transport_gates  # noqa: E402
from tools.hostessctl import companion_session  # noqa: E402
from tools.hostessctl import connectivity_media_product_plan  # noqa: E402
from tools.hostessctl import connectivity_media_receiver  # noqa: E402
from tools.hostessctl import connectivity_probe  # noqa: E402
from tools.hostessctl import connectivity_suite  # noqa: E402
from tools.hostessctl import device_link_report  # noqa: E402
from tools.hostessctl import live_capture_routes  # noqa: E402
from tools.hostessctl import makepad_pmb_setup  # noqa: E402
from tools.hostessctl import manifold_recording as manifold_recording_routes  # noqa: E402
from tools.hostessctl import native_breathing_room_setup  # noqa: E402
from tools.hostessctl import pmb_android_routes  # noqa: E402
from tools.hostessctl import pmb_desktop_routes  # noqa: E402
from tools.hostessctl import protocol_evidence_matrix  # noqa: E402
from tools.hostessctl import questionnaire_bridge  # noqa: E402
from tools.hostessctl import telemetry_routes  # noqa: E402
from tools.hostessctl.broker_transport import (  # noqa: E402
    MANIFOLD_BROKER_EVENTS_PATH,
    MANIFOLD_COMMAND_SCHEMA,
    BrokerWebSocketClient,
    accept_broker_stream_event,
    broker_ack_accepted,
    broker_command_message,
    connect_broker_websocket_with_retry,
    with_transport_event_aliases,
)
from tools.hostessctl.cli_parser import build_hostessctl_parser  # noqa: E402
from tools.hostessctl.manifold_recording import (  # noqa: E402
    adb_prefix,
    configure_makepad_controller_pose_provider,
    wait_for_makepad_controller_pose_ready,
)
from tools.hostessctl.platform_defaults import (  # noqa: E402
    ANDROID_ACTION,
    ANDROID_BROKER_TELEMETRY_ACTION,
    ANDROID_PACKAGE,
    ANDROID_PMB_CONTROLLER_PREFLIGHT_ACTION,
    ANDROID_PMB_PHYSICAL_LIVE_ACTION,
    ANDROID_PMB_PHYSICAL_LIVE_BACKGROUND_ACTION,
    ANDROID_PMB_PHYSICAL_LIVE_SERVICE,
    ANDROID_PMB_REPLAY_ACTION,
    ANDROID_PMB_SIMULATED_LIVE_ACTION,
    ANDROID_REMOTE_BROKER_TELEMETRY_EVIDENCE,
    ANDROID_REMOTE_BROKER_TELEMETRY_REPORT,
    ANDROID_REMOTE_EVIDENCE,
    ANDROID_REMOTE_GRAPH_REPORT,
    ANDROID_REMOTE_PMB_CONTROLLER_PREFLIGHT_EVIDENCE,
    ANDROID_REMOTE_PMB_CONTROLLER_PREFLIGHT_REPORT,
    ANDROID_REMOTE_PMB_CORE_REPORT,
    ANDROID_REMOTE_PMB_EVIDENCE,
    ANDROID_REMOTE_PMB_PHYSICAL_LIVE_BROKER_REPORT,
    ANDROID_REMOTE_PMB_PHYSICAL_LIVE_CAPTURE_REPORT,
    ANDROID_REMOTE_PMB_PHYSICAL_LIVE_EVENTS_JSONL,
    ANDROID_REMOTE_PMB_PHYSICAL_LIVE_EVIDENCE,
    ANDROID_REMOTE_PMB_PHYSICAL_LIVE_ROUTE_REPORT,
    ANDROID_REMOTE_PMB_SIMULATED_LIVE_BROKER_REPORT,
    ANDROID_REMOTE_PMB_SIMULATED_LIVE_EVIDENCE,
    ANDROID_REMOTE_PMB_SIMULATED_LIVE_ROUTE_REPORT,
    ANDROID_REMOTE_RENDER_ROOT,
    ANDROID_REMOTE_RUNTIME_INPUT,
    ANDROID_RENDER_ACTION,
    ANDROID_REPLAY_ACTION,
    BROKER_ACTIVITY,
    BROKER_LOCAL_FORWARD_PORT,
    BROKER_PACKAGE,
    BROKER_PORT,
    LEGACY_REFERENCE_BROKER_ACTIVITY,
    LEGACY_REFERENCE_BROKER_PACKAGE,
    MAKEPAD_ANDROID_ACTIVITY,
    MAKEPAD_ANDROID_PACKAGE,
    MAKEPAD_ANDROID_XR_ACTIVITY,
    MAKEPAD_PROVIDER_ACTIVITY,
    MAKEPAD_PROVIDER_PACKAGE,
    MAKEPAD_RENDER_RELATIVE,
    MAKEPAD_RENDER_SIDECAR_RELATIVE,
    MANIFOLD_BROKER_ACTIVITY,
    MANIFOLD_BROKER_PACKAGE,
    attach_broker_identity,
    broker_activity_for_package,
    broker_identity,
    selected_broker_activity,
    selected_broker_package,
)
from tools.hostessctl.pmb_broker_bridge import (  # noqa: E402
    listen_for_pmb_receipts,
    pmb_breath_payload,
    pmb_breath_source_kind,
    pmb_breath_source_stream_id,
    pmb_breath_state_payload,
    pmb_breath_state_value_payload,
    publish_pmb_feedback_samples,
    publish_pmb_stream_sample,
    sample_time_unix_ns_from_sample,
    select_pmb_output_samples,
    select_pmb_selected_breath_samples,
)
from tools.hostessctl.pmb_evidence import (  # noqa: E402
    PMB_BREATH_FEEDBACK_RECEIPT_STREAM,
    PMB_BREATH_FEEDBACK_STATE_STREAM,
    PMB_BREATH_SCALE_SMOOTHING_ALPHA,
    PMB_BREATH_SCALE_VOLUME0,
    PMB_BREATH_SCALE_VOLUME1,
    PMB_BREATH_SELECTION_STATE_STREAM,
    PMB_BREATH_STATE_STREAM,
    PMB_BREATH_STATE_VALUE_STREAM,
    PMB_BREATH_VOLUME_CONTROLLER_STREAM,
    PMB_BREATH_VOLUME_POLAR_STREAM,
    PMB_BREATH_VOLUME_SELECTED_STREAM,
    PMB_BREATH_VOLUME_STREAM,
    build_pmb_desktop_replay_execution_evidence,
    build_pmb_live_route_self_test_evidence,
    build_pmb_shell_handoff_validation_evidence,
    default_pmb_shell_handoff_path,
    graph_report_streams,
    host_app_for,
    iso_to_epoch_ms,
    parse_pmb_core_report,
    projected_motion_breath_package_root,
    projected_motion_package_snapshot,
    validate_pmb_android_replay_execution_evidence,
    validate_pmb_controller_preflight_evidence,
    validate_pmb_desktop_replay_execution_evidence,
    validate_pmb_live_route_self_test_evidence,
    validate_pmb_quest_physical_live_evidence,
    validate_pmb_quest_simulated_live_evidence,
    validate_pmb_shell_handoff_validation_evidence,
    write_contract_evidence,
    write_pmb_android_host_run_evidence,
    write_pmb_controller_preflight_host_run_evidence,
    write_pmb_host_run_evidence,
    write_pmb_live_route_host_run_evidence,
    write_pmb_quest_physical_live_host_run_evidence,
    write_pmb_quest_simulated_live_host_run_evidence,
    write_pmb_shell_handoff_host_run_evidence,
)
from tools.hostessctl.recording_evidence import (  # noqa: E402
    build_manifold_value_recording_evidence,
    recording_segment,
    validate_broker_telemetry_observer_evidence,
    validate_broker_websocket_stream_recording_evidence,
    validate_manifold_value_recording_evidence,
    write_manifold_value_recording_host_run_evidence,
)
from tools.hostessctl.runtime import run, run_captured  # noqa: E402


MANIFOLD_VALUE_ALIASES = manifold_recording_routes.MANIFOLD_VALUE_ALIASES
MANIFOLD_VALUE_PROVIDERS = manifold_recording_routes.MANIFOLD_VALUE_PROVIDERS
normalize_manifold_recording_values = manifold_recording_routes.normalize_manifold_recording_values
host_profile_for_target = manifold_recording_routes.host_profile_for_target
manifold_value_provider_plan = manifold_recording_routes.manifold_value_provider_plan
manifold_recording_route_status = manifold_recording_routes.manifold_recording_route_status
pmb_live_processor_inputs_ready = manifold_recording_routes.pmb_live_processor_inputs_ready
single_value_live_capture_args = manifold_recording_routes.single_value_live_capture_args
polar_package_root = live_capture_routes.polar_package_root
pmb_physical_live_start_command = pmb_android_routes.pmb_physical_live_start_command


def main() -> int:
    parser = build_hostessctl_parser(
        broker_package=BROKER_PACKAGE,
        broker_port=BROKER_PORT,
        broker_local_forward_port=BROKER_LOCAL_FORWARD_PORT,
        makepad_android_package=MAKEPAD_ANDROID_PACKAGE,
        makepad_android_xr_activity=MAKEPAD_ANDROID_XR_ACTIVITY,
        makepad_provider_package=MAKEPAD_PROVIDER_PACKAGE,
        makepad_provider_activity=MAKEPAD_PROVIDER_ACTIVITY,
    )
    args = parser.parse_args()
    return dispatch_command(args)


def dispatch_command(args: argparse.Namespace) -> int:
    if args.command == "install-android":
        return install_android(args)
    if args.command == "run-live":
        return run_live_capture(args)
    if args.command == "run-replay":
        return run_replay_capture(args)
    if args.command == "run-pmb-replay":
        return run_pmb_replay_capture(args)
    if args.command == "run-pmb-controller-preflight":
        return run_pmb_controller_preflight(args)
    if args.command == "run-pmb-quest-simulated-live":
        return run_pmb_quest_simulated_live(args)
    if args.command == "run-pmb-quest-physical-live":
        return run_pmb_quest_physical_live(args)
    if args.command == "native-breathing-room":
        if args.native_breathing_room_command == "setup":
            return native_breathing_room_setup.run_native_breathing_room_setup(
                args,
                run_func=run,
            )
        return 2
    if args.command == "observe-broker-telemetry":
        return observe_broker_telemetry_ui(args)
    if args.command == "run-pmb-live-route-self-test":
        return run_pmb_live_route_self_test(args)
    if args.command == "run-pmb-shell-handoff":
        return run_pmb_shell_handoff(args)
    if args.command == "record-values":
        return run_manifold_value_recording(args)
    if args.command == "emit-bridge-route-evidence":
        return emit_bridge_route_evidence(args)
    if args.command == "emit-bridge-command-request":
        return bridge_command_routes.run_emit_bridge_command_request(args)
    if args.command == "run-bridge-command":
        return run_bridge_command(args)
    if args.command == "run-bridge-command-live-android":
        return bridge_command_live_android_routes.run_bridge_command_live_android(args)
    if args.command == "run-bridge-command-android":
        return run_bridge_command_android(args)
    if args.command == "companion-catalog":
        return companion_catalog.run_companion_catalog(args)
    if args.command == "companion-readiness":
        return companion_readiness.run_companion_readiness(args)
    if args.command == "companion-session":
        if args.session_command == "run":
            return companion_session.run_companion_session(args, run_captured_func=run_captured)
        if args.session_command == "history":
            return companion_session.run_companion_session_history(args)
        return 2
    if args.command == "companion-report":
        if args.companion_report_command == "projection":
            return companion_report_projection.run_companion_report_projection(args)
        if args.companion_report_command == "transport-gates":
            return companion_transport_gates.run_companion_transport_gates(args)
        return 2
    if args.command == "connectivity-probe":
        if args.connectivity_probe_command == "run":
            return connectivity_probe.run_connectivity_probe(args, run_captured_func=run_captured)
        if args.connectivity_probe_command == "wifi-direct-lifecycle-template":
            return connectivity_probe.run_wifi_direct_lifecycle_template(args)
        if args.connectivity_probe_command == "qcl082-product-media-plan":
            return connectivity_media_product_plan.run_qcl082_product_media_direct_wifi_plan(args)
        if args.connectivity_probe_command == "rmanvid1-receiver-capture":
            return connectivity_media_receiver.run_rmanvid1_receiver_capture(args)
        if args.connectivity_probe_command == "windows-firewall-rule":
            return connectivity_probe.run_windows_firewall_rule(args, run_captured_func=run_captured)
        if args.connectivity_probe_command == "stream-capability":
            return device_link_report.run_stream_capability_descriptor(args)
        if args.connectivity_probe_command == "test-suite":
            return device_link_report.run_install_test_suite_descriptor(args)
        if args.connectivity_probe_command == "run-suite":
            return connectivity_suite.run_connectivity_suite(args, run_captured_func=run_captured)
        if args.connectivity_probe_command == "protocol-matrix":
            return protocol_evidence_matrix.run_protocol_evidence_matrix(args)
        return 2
    if args.command == "render-telemetry":
        return render_telemetry(args)
    if args.command == "pull-makepad-render":
        return pull_makepad_render(args)
    if args.command == "launch-makepad-shell-contract":
        return launch_makepad_shell_contract(args)
    if args.command == "questionnaire-status":
        return questionnaire_status(args)
    if args.command == "questionnaire-open-block":
        return questionnaire_open_block(args)
    if args.command == "questionnaire-dismiss":
        return questionnaire_dismiss(args)
    if args.command == "questionnaire-serve":
        return questionnaire_serve(args)
    if args.command == "snapshot-telemetry":
        return snapshot_telemetry(args)
    return 2


def install_android(args: argparse.Namespace) -> int:
    return live_capture_routes.install_android(args, run_func=run)


def run_live_capture(args: argparse.Namespace) -> int:
    if not args.stream and not args.module:
        raise SystemExit("run-live requires --stream or at least one --module")
    if args.stream and args.module:
        raise SystemExit("run-live accepts either --stream or --module selections, not both")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if args.target == "desktop":
        return run_desktop_capture(args, out)
    return run_android_capture(args, out)


def run_desktop_capture(args: argparse.Namespace, out: Path) -> int:
    return live_capture_routes.run_desktop_capture(
        args,
        out,
        run_func=run,
        validate_evidence_func=validate_evidence,
    )


def run_replay_capture(args: argparse.Namespace) -> int:
    return live_capture_routes.run_replay_capture(
        args,
        run_func=run,
        run_android_replay_func=run_android_replay,
        validate_evidence_func=validate_evidence,
    )


def run_android_capture(args: argparse.Namespace, out: Path) -> int:
    return live_capture_routes.run_android_capture(
        args,
        out,
        run_func=run,
        clear_android_live_artifacts_func=clear_android_live_artifacts,
        wait_for_android_evidence_func=wait_for_android_evidence,
        pull_android_runtime_artifacts_func=pull_android_runtime_artifacts,
        append_rmssd_baseline_extras_func=append_rmssd_baseline_extras,
        validate_evidence_func=validate_evidence,
    )


def run_android_replay(args: argparse.Namespace) -> int:
    return live_capture_routes.run_android_replay(
        args,
        run_func=run,
        clear_android_live_artifacts_func=clear_android_live_artifacts,
        wait_for_android_evidence_func=wait_for_android_evidence,
        pull_android_runtime_artifacts_func=pull_android_runtime_artifacts,
        validate_evidence_func=validate_evidence,
    )


def run_pmb_replay_capture(args: argparse.Namespace) -> int:
    return pmb_desktop_routes.run_pmb_replay_capture(
        args,
        run_captured_func=run_captured,
        run_android_pmb_replay_func=run_android_pmb_replay,
    )


def run_pmb_live_route_self_test(args: argparse.Namespace) -> int:
    return pmb_desktop_routes.run_pmb_live_route_self_test(args, run_captured_func=run_captured)


def run_pmb_shell_handoff(args: argparse.Namespace) -> int:
    return pmb_desktop_routes.run_pmb_shell_handoff(args)


def run_android_pmb_replay(args: argparse.Namespace) -> int:
    return pmb_android_routes.run_android_pmb_replay(
        args,
        run_func=run,
        clear_android_pmb_artifacts_func=clear_android_pmb_artifacts,
        wait_for_android_file_func=wait_for_android_file,
    )


def run_pmb_controller_preflight(args: argparse.Namespace) -> int:
    return pmb_android_routes.run_pmb_controller_preflight(
        args,
        run_func=run,
        clear_android_pmb_controller_preflight_artifacts_func=clear_android_pmb_controller_preflight_artifacts,
        wait_for_android_file_func=wait_for_android_file,
    )


def run_pmb_quest_simulated_live(args: argparse.Namespace) -> int:
    return pmb_android_routes.run_pmb_quest_simulated_live(
        args,
        run_func=run,
        configure_makepad_breath_feedback_receiver_func=configure_makepad_breath_feedback_receiver,
        clear_android_pmb_simulated_live_artifacts_func=clear_android_pmb_simulated_live_artifacts,
        wait_for_android_file_func=wait_for_android_file,
        selected_broker_activity_func=selected_broker_activity,
        attach_broker_identity_func=attach_broker_identity,
    )


def run_pmb_quest_physical_live(args: argparse.Namespace) -> int:
    return pmb_android_routes.run_pmb_quest_physical_live(
        args,
        run_func=run,
        run_captured_func=run_captured,
        grant_broker_runtime_permissions_func=grant_broker_runtime_permissions,
        configure_makepad_physical_pmb_provider_func=configure_makepad_physical_pmb_provider,
        clear_android_pmb_physical_live_artifacts_func=clear_android_pmb_physical_live_artifacts,
        wait_for_android_file_func=wait_for_android_file,
        selected_broker_activity_func=selected_broker_activity,
        broker_identity_func=broker_identity,
        attach_broker_identity_func=attach_broker_identity,
    )


def observe_broker_telemetry_ui(args: argparse.Namespace) -> int:
    return broker_telemetry_routes.observe_broker_telemetry_ui(
        args,
        run_func=run,
        grant_broker_runtime_permissions_func=grant_broker_runtime_permissions,
        clear_android_broker_telemetry_artifacts_func=clear_android_broker_telemetry_artifacts,
        wait_for_android_file_func=wait_for_android_file,
        selected_broker_activity_func=selected_broker_activity,
        attach_broker_identity_func=attach_broker_identity,
        render_telemetry_func=render_telemetry,
    )


def run_manifold_value_recording(args: argparse.Namespace) -> int:
    return manifold_recording_routes.run_manifold_value_recording(
        args,
        run_live_capture_func=run_live_capture,
        record_broker_streams_func=record_broker_websocket_streams,
        broker_identity_func=broker_identity,
    )


def emit_bridge_route_evidence(args: argparse.Namespace) -> int:
    return bridge_route_evidence.run_emit_bridge_route_evidence(args)


def run_bridge_command(args: argparse.Namespace) -> int:
    return bridge_command_routes.run_bridge_command(args)


def run_bridge_command_android(args: argparse.Namespace) -> int:
    return bridge_command_android_routes.run_bridge_command_android(
        args,
        run_func=run,
        run_captured_func=run_captured,
    )


def record_broker_websocket_streams(
    args: argparse.Namespace,
    provider_plans: list[dict[str, Any]],
    out: Path,
) -> int:
    return manifold_recording_routes.record_broker_websocket_streams(
        args,
        provider_plans,
        out,
        run_captured_func=run_captured,
        selected_broker_activity_func=selected_broker_activity,
        broker_identity_func=broker_identity,
    )


def run_pmb_live_processor_bridge(
    args: argparse.Namespace,
    events_jsonl: Path,
    capture_out: Path,
) -> dict[str, Any]:
    return manifold_recording_routes.run_pmb_live_processor_bridge(
        args,
        events_jsonl,
        capture_out,
        run_captured_func=run_captured,
    )


def redact_command(command: list[str]) -> list[str]:
    return manifold_recording_routes.redact_command(command)


def configure_makepad_breath_feedback_receiver(args: argparse.Namespace) -> None:
    makepad_pmb_setup.configure_makepad_breath_feedback_receiver(args, run_func=run)


def configure_makepad_physical_pmb_provider(args: argparse.Namespace) -> None:
    makepad_pmb_setup.configure_makepad_physical_pmb_provider(args, run_func=run)


def grant_broker_runtime_permissions(args: argparse.Namespace) -> None:
    makepad_pmb_setup.grant_broker_runtime_permissions(
        args,
        run_func=run,
        selected_broker_package_func=selected_broker_package,
    )


def render_telemetry(args: argparse.Namespace) -> int:
    return telemetry_routes.render_telemetry(
        args,
        run_func=run,
        wait_for_android_file_func=wait_for_android_file,
    )


def pull_makepad_render(args: argparse.Namespace) -> int:
    return telemetry_routes.pull_makepad_render(
        args,
        run_func=run,
        wait_for_android_run_as_file_func=wait_for_android_run_as_file,
        wait_for_makepad_render_sidecar_func=wait_for_makepad_render_sidecar,
        pull_android_run_as_file_func=pull_android_run_as_file,
    )


def launch_makepad_shell_contract(args: argparse.Namespace) -> int:
    return telemetry_routes.launch_makepad_shell_contract(
        args,
        host_app_for_func=host_app_for,
        run_func=run,
        wait_for_android_run_as_file_func=wait_for_android_run_as_file,
        pull_android_run_as_file_func=pull_android_run_as_file,
        write_android_run_as_file_func=write_android_run_as_file,
    )


def questionnaire_status(args: argparse.Namespace) -> int:
    return questionnaire_bridge.questionnaire_status(args)


def questionnaire_open_block(args: argparse.Namespace) -> int:
    return questionnaire_bridge.questionnaire_open_block(args)


def questionnaire_dismiss(args: argparse.Namespace) -> int:
    return questionnaire_bridge.questionnaire_dismiss(args)


def questionnaire_serve(args: argparse.Namespace) -> int:
    return questionnaire_bridge.questionnaire_serve(args)


def snapshot_telemetry(args: argparse.Namespace) -> int:
    return telemetry_routes.snapshot_telemetry(args)


def shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\\''") + "'"


def append_rmssd_baseline_extras(command: list[str], args: argparse.Namespace) -> None:
    live_capture_routes.append_rmssd_baseline_extras(command, args)


def clear_android_live_artifacts(args: argparse.Namespace) -> None:
    android_artifacts.clear_android_live_artifacts(args, run_func=run)


def clear_android_pmb_artifacts(args: argparse.Namespace) -> None:
    android_artifacts.clear_android_pmb_artifacts(args, run_func=run)


def clear_android_pmb_controller_preflight_artifacts(args: argparse.Namespace) -> None:
    android_artifacts.clear_android_pmb_controller_preflight_artifacts(args, run_func=run)


def clear_android_pmb_simulated_live_artifacts(args: argparse.Namespace) -> None:
    android_artifacts.clear_android_pmb_simulated_live_artifacts(args, run_func=run)


def clear_android_pmb_physical_live_artifacts(args: argparse.Namespace) -> None:
    android_artifacts.clear_android_pmb_physical_live_artifacts(args, run_func=run)


def clear_android_broker_telemetry_artifacts(args: argparse.Namespace) -> None:
    android_artifacts.clear_android_broker_telemetry_artifacts(args, run_func=run)


def clear_android_files(args: argparse.Namespace, remote_paths: list[str]) -> None:
    android_artifacts.clear_android_files(args, remote_paths, run_func=run)


def wait_for_android_evidence(args: argparse.Namespace, timeout_seconds: float) -> None:
    android_artifacts.wait_for_android_evidence(
        args,
        timeout_seconds,
        wait_for_android_file_func=wait_for_android_file,
    )


def wait_for_android_file(args: argparse.Namespace, remote_path: str, timeout_seconds: float) -> None:
    android_artifacts.wait_for_android_file(args, remote_path, timeout_seconds, run_func=run)


def wait_for_android_run_as_file(
    args: argparse.Namespace,
    package: str,
    relative_path: str,
    timeout_seconds: float,
) -> None:
    android_artifacts.wait_for_android_run_as_file(
        args,
        package,
        relative_path,
        timeout_seconds,
        run_func=run,
    )


def pull_android_run_as_file(
    args: argparse.Namespace,
    package: str,
    relative_path: str,
    out: Path,
) -> None:
    android_artifacts.pull_android_run_as_file(args, package, relative_path, out)


def write_android_run_as_file(
    args: argparse.Namespace,
    package: str,
    relative_path: str,
    payload: bytes,
) -> None:
    android_artifacts.write_android_run_as_file(args, package, relative_path, payload)


def android_shell_quote(value: str) -> str:
    return android_artifacts.android_shell_quote(value)


def read_android_run_as_file(
    args: argparse.Namespace,
    package: str,
    relative_path: str,
) -> bytes:
    return android_artifacts.read_android_run_as_file(args, package, relative_path)


def wait_for_makepad_render_sidecar(
    args: argparse.Namespace,
    package: str,
    relative_path: str,
    timeout_seconds: float,
    *,
    target: str,
    min_events: int,
) -> None:
    android_artifacts.wait_for_makepad_render_sidecar(
        args,
        package,
        relative_path,
        timeout_seconds,
        target=target,
        min_events=min_events,
    )


def pull_android_runtime_artifacts(args: argparse.Namespace, out: Path) -> None:
    live_capture_routes.pull_android_runtime_artifacts(args, out, run_func=run)


def validate_evidence(args: argparse.Namespace, out: Path, host_profile: str) -> int:
    return live_capture_routes.validate_evidence(args, out, host_profile, run_func=run)


if __name__ == "__main__":
    raise SystemExit(main())
