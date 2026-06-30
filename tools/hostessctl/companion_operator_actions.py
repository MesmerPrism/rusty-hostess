"""CLI-equivalent operator action catalog for companion frontends."""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


HOSTESS_COMPANION_OPERATOR_ACTION_CATALOG_SCHEMA = (
    "rusty.hostess.companion.operator_action_catalog.v1"
)
HOSTESS_COMPANION_OPERATOR_ACTION_CATALOG_VALIDATION_SCHEMA = (
    "rusty.hostess.companion.operator_action_catalog.validation.v1"
)
HOSTESS_CTL_SCRIPT = r"tools\hostessctl\hostessctl.py"
HOSTESS_CTL = "python " + HOSTESS_CTL_SCRIPT + " "


PROTOCOL_MATRIX_CLI_ROUTE = (
    "$HostessCtl = '" + HOSTESS_CTL_SCRIPT + "'; "
    r"$MediaStreamSessionPlan = '<rusty-quest-media-stream-plan>'; "
    r"$ProductMediaPlan = 'target\connectivity-probe\qcl082-product-media-direct-wifi-plan.json'; "
    r"$DirectWifiProductMediaPlan = 'target\connectivity-probe\direct-wifi-product-media-acceptance-plan.json'; "
    r"$StartSourceRequest = 'target\connectivity-probe\media-stream-start-source.request.json'; "
    r"$StartSourceBridgeEvidence = 'target\connectivity-probe\media-stream-start-source.bridge-evidence.json'; "
    r"$RuntimeStatus = 'target\connectivity-probe\media-stream-start-source.live-android-execution.json'; "
    r"$StartSourceValidation = 'target\connectivity-probe\media-stream-start-source.validation-report.json'; "
    r"$StartSourceLogcat = 'target\connectivity-probe\media-stream-start-source.logcat.txt'; "
    r"$FirewallVerify = '<qcl082-tcp-firewall-verify>'; "
    r"$HostessCompanionWpfExe = '<HostessCompanion.Wpf.exe>'; "
    r"$Rmanvid1Capture = '<rmanvid1-capture>'; "
    r"$ReceiverSidecar = '<receiver-sidecar>'; "
    r"$ReceiverResult = 'target\connectivity-probe\media-stream-receiver-result.json'; "
    r"$Qcl082SessionReport = 'target\connectivity-probe\qcl082-media-stream-session-plan.json'; "
    r"$Qcl082RuntimeStatusReport = 'target\connectivity-probe\qcl082-runtime-status-from-live-execution.json'; "
    r"$Qcl082ReceiverReport = 'target\connectivity-probe\qcl082-rmanvid1-receiver-capture.json'; "
    r"$Qcl079HostLoopbackReport = 'target\connectivity-probe\qcl079-websocket-loopback.json'; "
    r"$Qcl079ManifoldWebSocketReport = 'target\connectivity-probe\qcl079-manifold-websocket-stream.json'; "
    r"$PromotedTopologyReport = '<promoted-qcl040-or-qcl041-topology-report>'; "
    r"$ManifoldWebSocketRoute = '<manifold-stream-websocket-route>'; "
    r"$ManifoldWebSocketEvidence = '<manifold-stream-websocket-evidence>'; "
    r"$TopologyFixtureReports = '<topology-fixture-reports>'; "
    r"$Adb = '<adb>'; "
    r"$QuestSerial = '<quest-serial>'; "
    r"$QuestLeaseId = '<quest-lease-id>'; "
    r"$QuestLeaseResource = 'quest:<quest-serial>'; "
    r"$Qcl040Preflight = '<qcl040-live-wifi-direct-preflight>'; "
    r"$Qcl041Preflight = '<qcl041-live-wifi-direct-preflight>'; "
    r"$LifecycleReport = '<wifi-direct-lifecycle-report>'; "
    r"$Qcl040LifecyclePlan = 'target\connectivity-probe\qcl040-wifi-direct-lifecycle-plan.json'; "
    r"$Qcl041LifecyclePlan = 'target\connectivity-probe\qcl041-wifi-direct-lifecycle-plan.json'; "
    r"$Qcl040LifecycleTemplate = 'target\connectivity-probe\qcl040-wifi-direct-lifecycle-template.json'; "
    r"$Qcl041LifecycleTemplate = 'target\connectivity-probe\qcl041-wifi-direct-lifecycle-template.json'; "
    r"$Qcl040LifecycleReport = 'target\connectivity-probe\qcl040-live-wifi-direct-lifecycle.json'; "
    r"$Qcl041LifecycleReport = 'target\connectivity-probe\qcl041-live-wifi-direct-lifecycle.json'; "
    r"$Qcl020TopologyReport = 'target\connectivity-probe\qcl020-wifi-adb-session-pass.json'; "
    r"$Qcl030TopologyReport = 'target\connectivity-probe\qcl030-local-only-hotspot-started.json'; "
    r"$Qcl040TopologyFixtureReport = 'target\connectivity-probe\qcl040-wifi-direct-phone-peer-pass.json'; "
    r"$Qcl041TopologyFixtureReport = 'target\connectivity-probe\qcl041-wifi-direct-windows-peer-pass.json'; "
    r"$SuiteRun = '<suite-run>'; "
    r"$LatestArtifactDir = 'target\connectivity-probe'; "
    r"$LatestDeviceLinkDir = 'target\companion-session'; "
    r"$LatestStreamCapabilityDir = 'target\connectivity-probe'; "
    r"$TopologyFixtureInputs = @('--input', $Qcl020TopologyReport, '--input', $Qcl030TopologyReport, '--input', $Qcl040TopologyFixtureReport, '--input', $Qcl041TopologyFixtureReport); "
    r"$LifecycleTopologyInputs = @('--input', $Qcl040LifecycleReport, '--input', $Qcl041LifecycleReport); "
    r"$LatestProbeArgs = @('--latest-probe-id', 'QCL-000', '--latest-probe-id', 'QCL-010', '--latest-probe-id', 'QCL-011', '--latest-probe-id', 'QCL-020', '--latest-probe-id', 'QCL-030', '--latest-probe-id', 'QCL-040', '--latest-probe-id', 'QCL-041', '--latest-probe-id', 'QCL-050', '--latest-probe-id', 'QCL-051', '--latest-probe-id', 'QCL-080', '--latest-probe-id', 'QCL-081', '--latest-probe-id', 'QCL-082', '--latest-probe-id', 'QCL-083', '--latest-probe-id', 'QCL-084', '--latest-probe-id', 'QCL-079'); "
    r"$ProtocolMatrix = '<protocol-matrix>'; "
    r"$Projection = '<projection>'; "
    r"$TransportGates = '<transport-gates>'; "
    r"python $HostessCtl connectivity-probe qcl082-product-media-plan --out $ProductMediaPlan --promoted-topology-report $PromotedTopologyReport --firewall-report $FirewallVerify --adb $Adb --serial $QuestSerial --quest-lease-id $QuestLeaseId --quest-lease-resource $QuestLeaseResource; "
    r"python $HostessCtl connectivity-probe direct-wifi-product-media-plan --out $DirectWifiProductMediaPlan --qcl040-topology-report $Qcl040LifecycleReport --qcl041-topology-report $Qcl041LifecycleReport --promoted-topology-report $PromotedTopologyReport --firewall-report $FirewallVerify --qcl082-report $Qcl082ReceiverReport --adb $Adb --serial $QuestSerial --quest-lease-id $QuestLeaseId --quest-lease-resource $QuestLeaseResource; "
    r"python $HostessCtl connectivity-probe run --probe-id QCL-082 --media-stream-session-plan $MediaStreamSessionPlan --out $Qcl082SessionReport; "
    r"python $HostessCtl emit-bridge-command-request --bridge-command command.media_stream.start_source --request-id request.hostess.qcl082.media_stream.start_source --evidence-id evidence.hostess.qcl082.media_stream.start_source --route-id bridge_route.command.websocket.applied --required-stage sent --required-stage transport_ok --required-stage authority_accepted --out $StartSourceRequest; "
    r"python $HostessCtl run-bridge-command-live-android --input $StartSourceRequest --out $StartSourceBridgeEvidence --execution-out $RuntimeStatus --validation-out $StartSourceValidation --adb $Adb --serial $QuestSerial; "
    r"python $HostessCtl connectivity-probe run --probe-id QCL-082 --media-stream-runtime-status $RuntimeStatus --out $Qcl082RuntimeStatusReport; "
    r"python $HostessCtl connectivity-probe windows-firewall-rule --action verify --rule-profile qcl-082-rmanvid1-media --program $HostessCompanionWpfExe --out $FirewallVerify; "
    r"python $HostessCtl connectivity-probe qcl082-product-media-live-session --bridge-command command.media_stream.start_source --start-source-request-out $StartSourceRequest --bridge-evidence-out $StartSourceBridgeEvidence --execution-out $RuntimeStatus --validation-out $StartSourceValidation --logcat-out $StartSourceLogcat --capture-out $Rmanvid1Capture --sidecar-out $ReceiverSidecar --topology-report $PromotedTopologyReport --firewall-report $FirewallVerify --adb $Adb --serial $QuestSerial --quest-lease-id $QuestLeaseId --quest-lease-resource $QuestLeaseResource --quest-lease-reserved-before-live-steps --out $ReceiverResult; "
    r"python $HostessCtl connectivity-probe rmanvid1-receiver-capture --capture-kind live_broker_stream --capture-out $Rmanvid1Capture --sidecar-out $ReceiverSidecar --runtime-status $RuntimeStatus --topology-report $PromotedTopologyReport --firewall-report $FirewallVerify --quest-lease-id $QuestLeaseId --quest-lease-resource $QuestLeaseResource --quest-lease-reserved-before-live-steps --out $ReceiverResult; "
    r"python $HostessCtl connectivity-probe run --probe-id QCL-082 --media-stream-receiver-result $ReceiverResult --out $Qcl082ReceiverReport; "
    r"python $HostessCtl connectivity-probe run --probe-id QCL-079 --websocket-source host-loopback --out $Qcl079HostLoopbackReport; "
    r"python $HostessCtl connectivity-probe run --probe-id QCL-079 --websocket-source broker-owned-websocket --websocket-route-descriptor $ManifoldWebSocketRoute --websocket-route-evidence $ManifoldWebSocketEvidence --out $Qcl079ManifoldWebSocketReport; "
    r"python $HostessCtl connectivity-probe run-suite --out $SuiteRun; "
    r"python $HostessCtl connectivity-probe run --mode fixture --probe-id QCL-020 --fixture-profile qcl-020-wifi-adb-session-pass --out $Qcl020TopologyReport; "
    r"python $HostessCtl connectivity-probe run --mode fixture --probe-id QCL-030 --fixture-profile qcl-030-local-only-hotspot-started --out $Qcl030TopologyReport; "
    r"python $HostessCtl connectivity-probe run --mode fixture --probe-id QCL-040 --fixture-profile qcl-040-wifi-direct-phone-peer-pass --out $Qcl040TopologyFixtureReport; "
    r"python $HostessCtl connectivity-probe run --mode fixture --probe-id QCL-041 --fixture-profile qcl-041-wifi-direct-windows-peer-pass --out $Qcl041TopologyFixtureReport; "
    r"python $HostessCtl connectivity-probe wifi-direct-lifecycle-plan --probe-id QCL-040 --out $Qcl040LifecyclePlan --adb $Adb --serial $QuestSerial; "
    r"python $HostessCtl connectivity-probe wifi-direct-lifecycle-plan --probe-id QCL-041 --out $Qcl041LifecyclePlan --adb $Adb --serial $QuestSerial; "
    r"python $HostessCtl connectivity-probe run --mode live --probe-id QCL-040 --adb $Adb --serial $QuestSerial --out $Qcl040Preflight; "
    r"python $HostessCtl connectivity-probe run --mode live --probe-id QCL-041 --adb $Adb --serial $QuestSerial --out $Qcl041Preflight; "
    r"python $HostessCtl connectivity-probe wifi-direct-lifecycle-template --probe-id QCL-040 --out $Qcl040LifecycleTemplate; "
    r"python $HostessCtl connectivity-probe wifi-direct-lifecycle-template --probe-id QCL-041 --out $Qcl041LifecycleTemplate; "
    r"python $HostessCtl connectivity-probe run --mode fixture --probe-id QCL-040 --wifi-direct-lifecycle-report $LifecycleReport --out $Qcl040LifecycleReport --fail-on-error; "
    r"python $HostessCtl connectivity-probe run --mode fixture --probe-id QCL-041 --wifi-direct-lifecycle-report $LifecycleReport --out $Qcl041LifecycleReport --fail-on-error; "
    r"python $HostessCtl connectivity-probe protocol-matrix --suite-run $SuiteRun @TopologyFixtureInputs @LifecycleTopologyInputs --latest-artifact-dir $LatestArtifactDir @LatestProbeArgs --latest-device-link-dir $LatestDeviceLinkDir --latest-stream-capability-dir $LatestStreamCapabilityDir --latest-stream-probe-id QCL-080 --out $ProtocolMatrix; "
    r"python $HostessCtl companion-report projection --protocol-matrix $ProtocolMatrix --include-protocol-matrix-inputs --suite-run $SuiteRun --out $Projection; "
    r"python $HostessCtl companion-report transport-gates --projection $Projection --out $TransportGates --fail-on-pending --fail-on-incomplete"
)


def run_companion_operator_actions(
    args: argparse.Namespace,
    *,
    clock_func: Callable[[], datetime] | None = None,
) -> int:
    """Write the frontend operator action catalog and validation sidecar."""

    report = build_companion_operator_action_catalog(
        args,
        clock_func=clock_func or utc_now,
    )
    validation = validate_companion_operator_action_catalog(report)

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


def build_companion_operator_action_catalog(
    args: argparse.Namespace,
    *,
    clock_func: Callable[[], datetime],
) -> dict[str, Any]:
    generated_at = clock_func()
    frontend = str(getattr(args, "frontend", None) or "wpf")
    report_id = str(getattr(args, "report_id", None) or "").strip()
    if not report_id:
        report_id = f"{frontend}-operator-actions-{generated_at.strftime('%Y%m%d-%H%M%S')}"
    actions = operator_actions_for_frontend(frontend)
    issues = operator_catalog_issues(actions, frontend=frontend)
    segments = [
        segment
        for action in actions
        for segment in hostess_cli_segments(str(action.get("cli_route") or ""))
    ]
    return {
        "$schema": HOSTESS_COMPANION_OPERATOR_ACTION_CATALOG_SCHEMA,
        "schema_version": 1,
        "report_id": report_id,
        "frontend": frontend,
        "generated_at_utc": generated_at.isoformat().replace("+00:00", "Z"),
        "status": "fail" if any_error(issues) else "pass",
        "authority": {
            "ui_role": "requester_and_inspector",
            "catalog_only": True,
            "acceptance_owner": "advertised_cli_routes",
            "command_authority": "hostessctl_routes_and_source_reports",
            "policy": (
                "This catalog makes WPF-visible operator actions inspectable "
                "from the CLI. It does not execute commands, choose latest "
                "artifacts, change firewall/device state, run probes, reserve "
                "leases, or promote protocols."
            ),
        },
        "summary": {
            "action_count": len(actions),
            "hostess_cli_segment_count": len(segments),
            "all_hostess_cli_segments_name_out": not any(
                issue.get("issue_code")
                == "hostess.issue.operator_action_catalog.cli_segment_missing_out"
                for issue in issues
            ),
            "issue_count": len(issues),
        },
        "actions": actions,
        "issues": issues,
    }


def operator_actions_for_frontend(frontend: str) -> list[dict[str, Any]]:
    if frontend != "wpf":
        return []
    return [
        action(
            "wpf.readiness.refresh",
            "Refresh readiness and catalog",
            "RefreshCommand",
            r"$ReadinessReport = 'target\companion-readiness\wpf-readiness.json'; "
            r"$CatalogReport = 'target\companion-catalog\wpf-catalog.json'; "
            + HOSTESS_CTL
            + "companion-readiness --out $ReadinessReport; "
            + HOSTESS_CTL
            + "companion-catalog --out $CatalogReport",
            "rusty.hostess.companion.readiness_report.v1; rusty.hostess.companion.catalog.v1",
            "Hostess",
            "tools.test_hostessctl_companion_readiness; tools.test_hostessctl_companion_catalog; HostessCompanion.Wpf.Tests",
        ),
        action(
            "wpf.session.run",
            "Run companion session",
            "RunSessionCommand",
            r"$SessionReport = 'target\companion-session\wpf-session.json'; "
            + HOSTESS_CTL
            + "companion-session run --out $SessionReport --frontend wpf --profile hostess-makepad-quest "
            "--wait-seconds 30 --fallback-wait-seconds 30 --authority-wait-seconds 30 "
            "--broker-process-wait-seconds 20 --makepad-process-wait-seconds 20 "
            "--socket-wait-seconds 20 --launch-settle-seconds 8 "
            "--runtime-subscriber-retry-count 8 --runtime-subscriber-retry-wait-seconds 2",
            "rusty.hostess.companion.session.v1; rusty.quest.device_link.v1",
            "Hostess",
            "tools.test_hostessctl_companion_session; HostessCompanion.Wpf.Tests",
        ),
        action(
            "wpf.session.history",
            "Load session history",
            "LoadSessionHistoryCommand",
            r"$SessionHistory = 'target\companion-session\history.json'; "
            + HOSTESS_CTL
            + "companion-session history --out $SessionHistory",
            "rusty.hostess.companion.session_history.v1",
            "Hostess",
            "tools.test_hostessctl_companion_session; HostessCompanion.Wpf.Tests",
        ),
        action(
            "wpf.session.load_selected",
            "Load selected session",
            "LoadSelectedSessionCommand",
            HOSTESS_CTL
            + r"companion-session history --out target\companion-session\history.json; "
            "$SelectedSessionReport = '<rusty.hostess.companion.session.v1 report_path>'; "
            "Get-Content -LiteralPath $SelectedSessionReport",
            "rusty.hostess.companion.session.v1",
            "Hostess",
            "tools.test_hostessctl_companion_session; HostessCompanion.Wpf.Tests",
        ),
        action(
            "wpf.command.safe_probe",
            "Run safe bridge probe",
            "RunProbeCommand",
            r"$PrimaryEvidence = 'target\companion-command\wpf-broker-stream-probe-evidence.json'; "
            r"$PrimaryInput = 'fixtures\bridge-command\hostess-broker-stream-command-request.json'; "
            r"$FallbackEvidence = 'target\companion-command\wpf-app-private-probe-evidence.json'; "
            r"$FallbackInput = 'fixtures\bridge-command\hostess-android-hotload-command-request.json'; "
            r"$Adb = '<adb>'; "
            r"$QuestSerial = '<quest-serial>'; "
            + HOSTESS_CTL
            + "run-bridge-command-live-android --input $PrimaryInput --out $PrimaryEvidence --adb $Adb --serial $QuestSerial; "
            "if ($LASTEXITCODE -ne 0) { "
            + HOSTESS_CTL
            + "run-bridge-command-android --input $FallbackInput --out $FallbackEvidence --adb $Adb --serial $QuestSerial }",
            "rusty.hostess.bridge_command.live_android_execution_evidence.v1",
            "Hostess / Manifold / Rusty Quest",
            "tools.test_hostessctl_bridge_command_live_android; HostessCompanion.Wpf.Tests",
        ),
        action(
            "wpf.connectivity.firewall.plan",
            "Plan firewall rule",
            "PlanFirewallRuleCommand",
            r"$FirewallPlan = 'target\connectivity-probe\wpf-firewall-rule-plan.json'; "
            + HOSTESS_CTL
            + "connectivity-probe windows-firewall-rule --action plan --rule-profile '<rule-profile>' --out $FirewallPlan",
            "rusty.quest.connectivity_windows_firewall_rule.v1",
            "Hostess",
            "tools.test_hostessctl_connectivity_probe; HostessCompanion.Wpf.Tests",
        ),
        action(
            "wpf.connectivity.firewall.apply",
            "Apply firewall rule",
            "ApplyFirewallRuleCommand",
            r"$FirewallApply = 'target\connectivity-probe\wpf-firewall-rule-apply.json'; "
            r"$AdminHandoffScript = 'target\connectivity-probe\wpf-firewall-rule-apply.admin-handoff.ps1'; "
            r"$VerifyReport = 'target\connectivity-probe\wpf-firewall-rule-apply.verify.json'; "
            + HOSTESS_CTL
            + "connectivity-probe windows-firewall-rule --action apply --rule-profile '<rule-profile>' --out $FirewallApply --handoff-script-out $AdminHandoffScript --handoff-verify-out $VerifyReport",
            "rusty.quest.connectivity_windows_firewall_rule.v1",
            "Hostess",
            "tools.test_hostessctl_connectivity_probe; HostessCompanion.Wpf.Tests",
        ),
        action(
            "wpf.connectivity.firewall.verify",
            "Verify firewall rule",
            "VerifyFirewallRuleCommand",
            r"$FirewallVerify = 'target\connectivity-probe\wpf-firewall-rule-verify.json'; "
            + HOSTESS_CTL
            + "connectivity-probe windows-firewall-rule --action verify --rule-profile '<rule-profile>' --out $FirewallVerify",
            "rusty.quest.connectivity_windows_firewall_rule.v1",
            "Hostess",
            "tools.test_hostessctl_connectivity_probe; HostessCompanion.Wpf.Tests",
        ),
        action(
            "wpf.connectivity.verify",
            "Verify connectivity",
            "VerifyConnectivityCommand",
            r"$ConnectivityReport = 'target\connectivity-probe\wpf-connectivity-verify.json'; "
            r"$StreamCapability = 'target\connectivity-probe\wpf-connectivity-verify.stream-capability.json'; "
            "$ProbeId = '<QCL-010-or-QCL-080>'; "
            "$Adb = '<adb>'; "
            "$QuestSerial = '<quest-serial>'; "
            "$HostessCompanionWpfExe = '<HostessCompanion.Wpf.exe>'; "
            "$TcpEchoPort = 18766; "
            "$UdpPort = 18767; "
            "if ($ProbeId -eq 'QCL-080') { "
            + HOSTESS_CTL
            + "connectivity-probe run --mode live --probe-id QCL-080 --out $ConnectivityReport --adb $Adb --serial $QuestSerial --udp-port $UdpPort --udp-sender-source makepad-runtime --udp-listener-helper $HostessCompanionWpfExe; "
            + HOSTESS_CTL
            + "connectivity-probe stream-capability --input $ConnectivityReport --out $StreamCapability } "
            "else { "
            + HOSTESS_CTL
            + "connectivity-probe run --mode live --probe-id QCL-010 --out $ConnectivityReport --adb $Adb --serial $QuestSerial --tcp-echo-port $TcpEchoPort }",
            "rusty.hostess.connectivity_probe.v1; rusty.quest.device_link.stream_capability.v1",
            "Hostess / Rusty Quest",
            "tools.test_hostessctl_connectivity_probe; tools.test_hostessctl_device_link_report; HostessCompanion.Wpf.Tests",
        ),
        action(
            "wpf.connectivity.suite",
            "Run connectivity suite",
            "RunConnectivitySuiteCommand",
            r"$ConnectivitySuite = 'target\connectivity-probe\wpf-connectivity-suite.json'; "
            r"$ConnectivitySuiteArtifacts = 'target\connectivity-probe\wpf-connectivity-suite-artifacts'; "
            "$HostessCompanionWpfExe = '<HostessCompanion.Wpf.exe>'; "
            "$Adb = '<adb>'; "
            "$QuestSerial = '<quest-serial>'; "
            + HOSTESS_CTL
            + "connectivity-probe run-suite --mode fixture --suite-id wpf-connectivity-suite --out $ConnectivitySuite --artifact-dir $ConnectivitySuiteArtifacts --listener-program $HostessCompanionWpfExe --listener-protocol '<TCP-or-UDP>' --listener-port '<port>' --adb $Adb --serial $QuestSerial",
            "rusty.quest.device_link.install_environment_suite_run.v1",
            "Hostess",
            "tools.test_hostessctl_connectivity_suite; HostessCompanion.Wpf.Tests",
        ),
        action(
            "wpf.connectivity.protocol_matrix",
            "Build protocol matrix",
            "RunProtocolMatrixCommand",
            PROTOCOL_MATRIX_CLI_ROUTE,
            "rusty.quest.device_link.protocol_evidence_matrix.v1; rusty.quest.connectivity_topology_probe.v1; rusty.hostess.direct_wifi_product_media_acceptance_plan.v1; rusty.hostess.companion.report_projection.v1; rusty.hostess.companion.transport_gate_report.v1",
            "Hostess / Rusty Quest / Manifold",
            "tools.test_hostessctl_protocol_evidence_matrix; tools.test_hostessctl_companion_report_projection; HostessCompanion.Wpf.Tests",
        ),
        action(
            "wpf.connectivity.firewall.remove",
            "Remove firewall rule",
            "RemoveFirewallRuleCommand",
            r"$FirewallRemove = 'target\connectivity-probe\wpf-firewall-rule-remove.json'; "
            r"$AdminHandoffScript = 'target\connectivity-probe\wpf-firewall-rule-remove.admin-handoff.ps1'; "
            r"$VerifyReport = 'target\connectivity-probe\wpf-firewall-rule-remove.verify.json'; "
            + HOSTESS_CTL
            + "connectivity-probe windows-firewall-rule --action remove --rule-profile '<rule-profile>' --out $FirewallRemove --handoff-script-out $AdminHandoffScript --handoff-verify-out $VerifyReport",
            "rusty.quest.connectivity_windows_firewall_rule.v1",
            "Hostess",
            "tools.test_hostessctl_connectivity_probe; HostessCompanion.Wpf.Tests",
        ),
    ]


def action(
    action_id: str,
    title: str,
    ui_command_property: str,
    cli_route: str,
    evidence_artifact: str,
    authority_owner: str,
    test_coverage: str,
) -> dict[str, Any]:
    return {
        "action_id": action_id,
        "title": title,
        "ui_command_property": ui_command_property,
        "cli_route": cli_route,
        "evidence_artifact": evidence_artifact,
        "authority_owner": authority_owner,
        "test_coverage": test_coverage,
    }


def validate_companion_operator_action_catalog(report: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if report.get("$schema") != HOSTESS_COMPANION_OPERATOR_ACTION_CATALOG_SCHEMA:
        errors.append("unsupported companion operator action catalog schema")
    authority = object_value(report.get("authority"))
    if authority.get("catalog_only") is not True:
        errors.append("operator action catalog must set catalog_only=true")
    actions = list_objects(report.get("actions"))
    if not actions:
        errors.append("actions must not be empty")
    seen: set[str] = set()
    for action_row in actions:
        action_id = str(action_row.get("action_id") or "")
        if not action_id:
            errors.append("action missing action_id")
        elif action_id in seen:
            errors.append(f"duplicate action_id: {action_id}")
        else:
            seen.add(action_id)
        for field in [
            "title",
            "ui_command_property",
            "cli_route",
            "evidence_artifact",
            "authority_owner",
            "test_coverage",
        ]:
            if not str(action_row.get(field) or "").strip():
                errors.append(f"action {action_id or '<unknown>'} missing {field}")
    for catalog_issue in list_objects(report.get("issues")):
        message = str(catalog_issue.get("message") or catalog_issue.get("issue_code") or "")
        if catalog_issue.get("severity") == "error":
            errors.append(message)
        else:
            warnings.append(message)
    return {
        "$schema": HOSTESS_COMPANION_OPERATOR_ACTION_CATALOG_VALIDATION_SCHEMA,
        "status": "pass" if not errors else "fail",
        "report_id": report.get("report_id"),
        "frontend": report.get("frontend"),
        "action_count": len(actions),
        "errors": errors,
        "warnings": warnings,
    }


def operator_catalog_issues(
    actions: list[dict[str, Any]],
    *,
    frontend: str,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if frontend != "wpf":
        issues.append(
            issue(
                "hostess.issue.operator_action_catalog.unsupported_frontend",
                "error",
                f"unsupported operator action frontend {frontend}",
            )
        )
    for action_row in actions:
        action_id = str(action_row.get("action_id") or "")
        route = str(action_row.get("cli_route") or "")
        if not action_id.startswith(f"{frontend}."):
            issues.append(
                issue(
                    "hostess.issue.operator_action_catalog.action_id_scope",
                    "error",
                    f"action {action_id or '<unknown>'} is not scoped to {frontend}",
                    action_id=action_id,
                )
            )
        if not advertises_hostessctl(route):
            issues.append(
                issue(
                    "hostess.issue.operator_action_catalog.hostessctl_missing",
                    "error",
                    f"action {action_id or '<unknown>'} does not advertise hostessctl",
                    action_id=action_id,
                )
            )
        if re.search(r"[A-Za-z0-9_)-]\|[A-Za-z0-9_(]", route):
            issues.append(
                issue(
                    "hostess.issue.operator_action_catalog.pipe_shorthand",
                    "error",
                    f"action {action_id or '<unknown>'} uses pipe-delimited option shorthand",
                    action_id=action_id,
                )
            )
        for segment in hostess_cli_segments(route):
            if not re.search(r"(^|\s)--out(\s|$)", segment):
                issues.append(
                    issue(
                        "hostess.issue.operator_action_catalog.cli_segment_missing_out",
                        "error",
                        f"action {action_id or '<unknown>'} route segment missing --out: {segment}",
                        action_id=action_id,
                    )
                )
    return issues


def hostess_cli_segments(cli_route: str) -> list[str]:
    return [
        segment
        for segment in [
            part.strip()
            for part in cli_route.split(";")
            if part.strip()
        ]
        if (
            f"python {HOSTESS_CTL_SCRIPT}" in segment
            or "python $HostessCtl" in segment
        )
    ]


def advertises_hostessctl(cli_route: str) -> bool:
    return (
        f"python {HOSTESS_CTL_SCRIPT}" in cli_route
        or (
            f"$HostessCtl = '{HOSTESS_CTL_SCRIPT}'" in cli_route
            and "python $HostessCtl" in cli_route
        )
    )


def issue(
    issue_code: str,
    severity: str,
    message: str,
    *,
    action_id: str = "",
) -> dict[str, Any]:
    row = {
        "issue_code": issue_code,
        "severity": severity,
        "message": message,
    }
    if action_id:
        row["action_id"] = action_id
    return row


def any_error(issues: list[dict[str, Any]]) -> bool:
    return any(issue_row.get("severity") == "error" for issue_row in issues)


def object_value(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def list_objects(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def utc_now() -> datetime:
    return datetime.now(UTC)


__all__ = [
    "HOSTESS_COMPANION_OPERATOR_ACTION_CATALOG_SCHEMA",
    "HOSTESS_COMPANION_OPERATOR_ACTION_CATALOG_VALIDATION_SCHEMA",
    "build_companion_operator_action_catalog",
    "run_companion_operator_actions",
    "validate_companion_operator_action_catalog",
]
