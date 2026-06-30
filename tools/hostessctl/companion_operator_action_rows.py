"""Static operator action rows for companion frontends."""

from __future__ import annotations

from typing import Any


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


__all__ = [
    "HOSTESS_CTL_SCRIPT",
    "operator_actions_for_frontend",
]
