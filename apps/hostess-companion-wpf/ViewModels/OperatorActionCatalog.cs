namespace HostessCompanion.Wpf.ViewModels;

public static class OperatorActionCatalog
{
    private const string HostessCtlScript = "tools\\hostessctl\\hostessctl.py";
    private const string HostessCtl = "python " + HostessCtlScript + " ";
    private const string ProtocolMatrixCliRoute =
        "$HostessCtl = '" + HostessCtlScript + "'; " +
        "$MediaStreamSessionPlan = '<rusty-quest-media-stream-plan>'; " +
        "$ProductMediaPlan = 'target\\connectivity-probe\\qcl082-product-media-direct-wifi-plan.json'; " +
        "$DirectWifiProductMediaPlan = 'target\\connectivity-probe\\direct-wifi-product-media-acceptance-plan.json'; " +
        "$StartSourceRequest = 'target\\connectivity-probe\\media-stream-start-source.request.json'; " +
        "$StartSourceBridgeEvidence = 'target\\connectivity-probe\\media-stream-start-source.bridge-evidence.json'; " +
        "$RuntimeStatus = 'target\\connectivity-probe\\media-stream-start-source.live-android-execution.json'; " +
        "$StartSourceValidation = 'target\\connectivity-probe\\media-stream-start-source.validation-report.json'; " +
        "$StartSourceLogcat = 'target\\connectivity-probe\\media-stream-start-source.logcat.txt'; " +
        "$FirewallVerify = '<qcl082-tcp-firewall-verify>'; " +
        "$HostessCompanionWpfExe = '<HostessCompanion.Wpf.exe>'; " +
        "$Rmanvid1Capture = '<rmanvid1-capture>'; " +
        "$ReceiverSidecar = '<receiver-sidecar>'; " +
        "$ReceiverResult = 'target\\connectivity-probe\\media-stream-receiver-result.json'; " +
        "$Qcl082SessionReport = 'target\\connectivity-probe\\qcl082-media-stream-session-plan.json'; " +
        "$Qcl082RuntimeStatusReport = 'target\\connectivity-probe\\qcl082-runtime-status-from-live-execution.json'; " +
        "$Qcl082ReceiverReport = 'target\\connectivity-probe\\qcl082-rmanvid1-receiver-capture.json'; " +
        "$Qcl079HostLoopbackReport = 'target\\connectivity-probe\\qcl079-websocket-loopback.json'; " +
        "$Qcl079ManifoldWebSocketReport = 'target\\connectivity-probe\\qcl079-manifold-websocket-stream.json'; " +
        "$PromotedTopologyReport = '<promoted-qcl040-or-qcl041-topology-report>'; " +
        "$ManifoldWebSocketRoute = '<manifold-stream-websocket-route>'; " +
        "$ManifoldWebSocketEvidence = '<manifold-stream-websocket-evidence>'; " +
        "$TopologyFixtureReports = '<topology-fixture-reports>'; " +
        "$Adb = '<adb>'; " +
        "$QuestSerial = '<quest-serial>'; " +
        "$QuestLeaseId = '<quest-lease-id>'; " +
        "$QuestLeaseResource = 'quest:<quest-serial>'; " +
        "$Qcl040Preflight = '<qcl040-live-wifi-direct-preflight>'; " +
        "$Qcl041Preflight = '<qcl041-live-wifi-direct-preflight>'; " +
        "$LifecycleReport = '<wifi-direct-lifecycle-report>'; " +
        "$Qcl040LifecyclePlan = 'target\\connectivity-probe\\qcl040-wifi-direct-lifecycle-plan.json'; " +
        "$Qcl041LifecyclePlan = 'target\\connectivity-probe\\qcl041-wifi-direct-lifecycle-plan.json'; " +
        "$Qcl040LifecycleTemplate = 'target\\connectivity-probe\\qcl040-wifi-direct-lifecycle-template.json'; " +
        "$Qcl041LifecycleTemplate = 'target\\connectivity-probe\\qcl041-wifi-direct-lifecycle-template.json'; " +
        "$Qcl040LifecycleReport = 'target\\connectivity-probe\\qcl040-live-wifi-direct-lifecycle.json'; " +
        "$Qcl041LifecycleReport = 'target\\connectivity-probe\\qcl041-live-wifi-direct-lifecycle.json'; " +
        "$Qcl020TopologyReport = 'target\\connectivity-probe\\qcl020-wifi-adb-session-pass.json'; " +
        "$Qcl030TopologyReport = 'target\\connectivity-probe\\qcl030-local-only-hotspot-started.json'; " +
        "$Qcl040TopologyFixtureReport = 'target\\connectivity-probe\\qcl040-wifi-direct-phone-peer-pass.json'; " +
        "$Qcl041TopologyFixtureReport = 'target\\connectivity-probe\\qcl041-wifi-direct-windows-peer-pass.json'; " +
        "$SuiteRun = '<suite-run>'; " +
        "$LatestArtifactDir = 'target\\connectivity-probe'; " +
        "$LatestDeviceLinkDir = 'target\\companion-session'; " +
        "$LatestStreamCapabilityDir = 'target\\connectivity-probe'; " +
        "$TopologyFixtureInputs = @('--input', $Qcl020TopologyReport, '--input', $Qcl030TopologyReport, '--input', $Qcl040TopologyFixtureReport, '--input', $Qcl041TopologyFixtureReport); " +
        "$LifecycleTopologyInputs = @('--input', $Qcl040LifecycleReport, '--input', $Qcl041LifecycleReport); " +
        "$LatestProbeArgs = @('--latest-probe-id', 'QCL-000', '--latest-probe-id', 'QCL-010', '--latest-probe-id', 'QCL-011', '--latest-probe-id', 'QCL-020', '--latest-probe-id', 'QCL-030', '--latest-probe-id', 'QCL-040', '--latest-probe-id', 'QCL-041', '--latest-probe-id', 'QCL-050', '--latest-probe-id', 'QCL-051', '--latest-probe-id', 'QCL-080', '--latest-probe-id', 'QCL-081', '--latest-probe-id', 'QCL-082', '--latest-probe-id', 'QCL-083', '--latest-probe-id', 'QCL-084', '--latest-probe-id', 'QCL-079'); " +
        "$ProtocolMatrix = '<protocol-matrix>'; " +
        "$Projection = '<projection>'; " +
        "$TransportGates = '<transport-gates>'; " +
        "python $HostessCtl connectivity-probe qcl082-product-media-plan --out $ProductMediaPlan --promoted-topology-report $PromotedTopologyReport --firewall-report $FirewallVerify --adb $Adb --serial $QuestSerial --quest-lease-id $QuestLeaseId --quest-lease-resource $QuestLeaseResource; " +
        "python $HostessCtl connectivity-probe direct-wifi-product-media-plan --out $DirectWifiProductMediaPlan --qcl040-topology-report $Qcl040LifecycleReport --qcl041-topology-report $Qcl041LifecycleReport --promoted-topology-report $PromotedTopologyReport --firewall-report $FirewallVerify --qcl082-report $Qcl082ReceiverReport --adb $Adb --serial $QuestSerial --quest-lease-id $QuestLeaseId --quest-lease-resource $QuestLeaseResource; " +
        "python $HostessCtl connectivity-probe run --probe-id QCL-082 --media-stream-session-plan $MediaStreamSessionPlan --out $Qcl082SessionReport; " +
        "python $HostessCtl emit-bridge-command-request --bridge-command command.media_stream.start_source --request-id request.hostess.qcl082.media_stream.start_source --evidence-id evidence.hostess.qcl082.media_stream.start_source --route-id bridge_route.command.websocket.applied --required-stage sent --required-stage transport_ok --required-stage authority_accepted --out $StartSourceRequest; " +
        "python $HostessCtl run-bridge-command-live-android --input $StartSourceRequest --out $StartSourceBridgeEvidence --execution-out $RuntimeStatus --validation-out $StartSourceValidation --adb $Adb --serial $QuestSerial; " +
        "python $HostessCtl connectivity-probe run --probe-id QCL-082 --media-stream-runtime-status $RuntimeStatus --out $Qcl082RuntimeStatusReport; " +
        "python $HostessCtl connectivity-probe windows-firewall-rule --action verify --rule-profile qcl-082-rmanvid1-media --program $HostessCompanionWpfExe --out $FirewallVerify; " +
        "python $HostessCtl connectivity-probe qcl082-product-media-live-session --bridge-command command.media_stream.start_source --start-source-request-out $StartSourceRequest --bridge-evidence-out $StartSourceBridgeEvidence --execution-out $RuntimeStatus --validation-out $StartSourceValidation --logcat-out $StartSourceLogcat --capture-out $Rmanvid1Capture --sidecar-out $ReceiverSidecar --topology-report $PromotedTopologyReport --firewall-report $FirewallVerify --adb $Adb --serial $QuestSerial --quest-lease-id $QuestLeaseId --quest-lease-resource $QuestLeaseResource --quest-lease-reserved-before-live-steps --out $ReceiverResult; " +
        "python $HostessCtl connectivity-probe rmanvid1-receiver-capture --capture-kind live_broker_stream --capture-out $Rmanvid1Capture --sidecar-out $ReceiverSidecar --runtime-status $RuntimeStatus --topology-report $PromotedTopologyReport --firewall-report $FirewallVerify --quest-lease-id $QuestLeaseId --quest-lease-resource $QuestLeaseResource --quest-lease-reserved-before-live-steps --out $ReceiverResult; " +
        "python $HostessCtl connectivity-probe run --probe-id QCL-082 --media-stream-receiver-result $ReceiverResult --out $Qcl082ReceiverReport; " +
        "python $HostessCtl connectivity-probe run --probe-id QCL-079 --websocket-source host-loopback --out $Qcl079HostLoopbackReport; " +
        "python $HostessCtl connectivity-probe run --probe-id QCL-079 --websocket-source broker-owned-websocket --websocket-route-descriptor $ManifoldWebSocketRoute --websocket-route-evidence $ManifoldWebSocketEvidence --out $Qcl079ManifoldWebSocketReport; " +
        "python $HostessCtl connectivity-probe run-suite --out $SuiteRun; " +
        "python $HostessCtl connectivity-probe run --mode fixture --probe-id QCL-020 --fixture-profile qcl-020-wifi-adb-session-pass --out $Qcl020TopologyReport; " +
        "python $HostessCtl connectivity-probe run --mode fixture --probe-id QCL-030 --fixture-profile qcl-030-local-only-hotspot-started --out $Qcl030TopologyReport; " +
        "python $HostessCtl connectivity-probe run --mode fixture --probe-id QCL-040 --fixture-profile qcl-040-wifi-direct-phone-peer-pass --out $Qcl040TopologyFixtureReport; " +
        "python $HostessCtl connectivity-probe run --mode fixture --probe-id QCL-041 --fixture-profile qcl-041-wifi-direct-windows-peer-pass --out $Qcl041TopologyFixtureReport; " +
        "python $HostessCtl connectivity-probe wifi-direct-lifecycle-plan --probe-id QCL-040 --out $Qcl040LifecyclePlan --adb $Adb --serial $QuestSerial; " +
        "python $HostessCtl connectivity-probe wifi-direct-lifecycle-plan --probe-id QCL-041 --out $Qcl041LifecyclePlan --adb $Adb --serial $QuestSerial; " +
        "python $HostessCtl connectivity-probe run --mode live --probe-id QCL-040 --adb $Adb --serial $QuestSerial --out $Qcl040Preflight; " +
        "python $HostessCtl connectivity-probe run --mode live --probe-id QCL-041 --adb $Adb --serial $QuestSerial --out $Qcl041Preflight; " +
        "python $HostessCtl connectivity-probe wifi-direct-lifecycle-template --probe-id QCL-040 --out $Qcl040LifecycleTemplate; " +
        "python $HostessCtl connectivity-probe wifi-direct-lifecycle-template --probe-id QCL-041 --out $Qcl041LifecycleTemplate; " +
        "python $HostessCtl connectivity-probe run --mode fixture --probe-id QCL-040 --wifi-direct-lifecycle-report $LifecycleReport --out $Qcl040LifecycleReport --fail-on-error; " +
        "python $HostessCtl connectivity-probe run --mode fixture --probe-id QCL-041 --wifi-direct-lifecycle-report $LifecycleReport --out $Qcl041LifecycleReport --fail-on-error; " +
        "python $HostessCtl connectivity-probe protocol-matrix --suite-run $SuiteRun @TopologyFixtureInputs @LifecycleTopologyInputs --latest-artifact-dir $LatestArtifactDir @LatestProbeArgs --latest-device-link-dir $LatestDeviceLinkDir --latest-stream-capability-dir $LatestStreamCapabilityDir --latest-stream-probe-id QCL-080 --out $ProtocolMatrix; " +
        "python $HostessCtl companion-report projection --protocol-matrix $ProtocolMatrix --include-protocol-matrix-inputs --suite-run $SuiteRun --out $Projection; " +
        "python $HostessCtl companion-report transport-gates --projection $Projection --out $TransportGates --fail-on-pending --fail-on-incomplete";

    public static IReadOnlyList<OperatorActionDescriptor> All { get; } =
    [
        new(
            "wpf.readiness.refresh",
            "Refresh readiness and catalog",
            "RefreshCommand",
            "$ReadinessReport = 'target\\companion-readiness\\wpf-readiness.json'; " +
            "$CatalogReport = 'target\\companion-catalog\\wpf-catalog.json'; " +
            HostessCtl + "companion-readiness --out $ReadinessReport; " +
            HostessCtl + "companion-catalog --out $CatalogReport",
            "rusty.hostess.companion.readiness_report.v1; rusty.hostess.companion.catalog.v1",
            "Hostess",
            "tools.test_hostessctl_companion_readiness; tools.test_hostessctl_companion_catalog; HostessCompanion.Wpf.Tests"),
        new(
            "wpf.session.run",
            "Run companion session",
            "RunSessionCommand",
            "$SessionReport = 'target\\companion-session\\wpf-session.json'; " +
            "$Adb = '<adb>'; " +
            "$QuestSerial = '<quest-serial>'; " +
            HostessCtl + "companion-session run --out $SessionReport --frontend wpf --profile hostess-makepad-quest " +
            "--adb $Adb --serial $QuestSerial " +
            "--wait-seconds 30 --fallback-wait-seconds 30 --authority-wait-seconds 30 " +
            "--broker-process-wait-seconds 20 --makepad-process-wait-seconds 20 " +
            "--socket-wait-seconds 20 --launch-settle-seconds 8 " +
            "--runtime-subscriber-retry-count 8 --runtime-subscriber-retry-wait-seconds 2",
            "rusty.hostess.companion.session.v1; rusty.quest.device_link.v1",
            "Hostess",
            "tools.test_hostessctl_companion_session; HostessCompanion.Wpf.Tests",
            RequiresQuestLease: true,
            MutatesHost: true,
            MutatesDevice: true),
        new(
            "wpf.session.history",
            "Load session history",
            "LoadSessionHistoryCommand",
            "$SessionHistory = 'target\\companion-session\\history.json'; " +
            HostessCtl + "companion-session history --out $SessionHistory",
            "rusty.hostess.companion.session_history.v1",
            "Hostess",
            "tools.test_hostessctl_companion_session; HostessCompanion.Wpf.Tests"),
        new(
            "wpf.session.load_selected",
            "Load selected session",
            "LoadSelectedSessionCommand",
            HostessCtl + "companion-session history --out target\\companion-session\\history.json; $SelectedSessionReport = '<rusty.hostess.companion.session.v1 report_path>'; Get-Content -LiteralPath $SelectedSessionReport",
            "rusty.hostess.companion.session.v1",
            "Hostess",
            "tools.test_hostessctl_companion_session; HostessCompanion.Wpf.Tests"),
        new(
            "wpf.command.safe_probe",
            "Run safe bridge probe",
            "RunProbeCommand",
            "$PrimaryEvidence = 'target\\companion-command\\wpf-broker-stream-probe-evidence.json'; " +
            "$PrimaryInput = 'fixtures\\bridge-command\\hostess-broker-stream-command-request.json'; " +
            "$FallbackEvidence = 'target\\companion-command\\wpf-app-private-probe-evidence.json'; " +
            "$FallbackInput = 'fixtures\\bridge-command\\hostess-android-hotload-command-request.json'; " +
            "$Adb = '<adb>'; " +
            "$QuestSerial = '<quest-serial>'; " +
            HostessCtl + "run-bridge-command-live-android --input $PrimaryInput --out $PrimaryEvidence --adb $Adb --serial $QuestSerial; " +
            "if ($LASTEXITCODE -ne 0) { " + HostessCtl + "run-bridge-command-android --input $FallbackInput --out $FallbackEvidence --adb $Adb --serial $QuestSerial }",
            "rusty.hostess.bridge_command.live_android_execution_evidence.v1",
            "Hostess / Manifold / Rusty Quest",
            "tools.test_hostessctl_bridge_command_live_android; HostessCompanion.Wpf.Tests",
            RequiresQuestLease: true,
            MutatesHost: true,
            MutatesDevice: true),
        new(
            "wpf.connectivity.firewall.plan",
            "Plan firewall rule",
            "PlanFirewallRuleCommand",
            "$FirewallPlan = 'target\\connectivity-probe\\wpf-firewall-rule-plan.json'; " +
            HostessCtl + "connectivity-probe windows-firewall-rule --action plan --rule-profile '<rule-profile>' --out $FirewallPlan",
            "rusty.quest.connectivity_windows_firewall_rule.v1",
            "Hostess",
            "tools.test_hostessctl_connectivity_probe; HostessCompanion.Wpf.Tests"),
        new(
            "wpf.connectivity.firewall.apply",
            "Apply firewall rule",
            "ApplyFirewallRuleCommand",
            "$FirewallApply = 'target\\connectivity-probe\\wpf-firewall-rule-apply.json'; " +
            "$AdminHandoffScript = 'target\\connectivity-probe\\wpf-firewall-rule-apply.admin-handoff.ps1'; " +
            "$VerifyReport = 'target\\connectivity-probe\\wpf-firewall-rule-apply.verify.json'; " +
            HostessCtl + "connectivity-probe windows-firewall-rule --action apply --rule-profile '<rule-profile>' --out $FirewallApply --handoff-script-out $AdminHandoffScript --handoff-verify-out $VerifyReport",
            "rusty.quest.connectivity_windows_firewall_rule.v1",
            "Hostess",
            "tools.test_hostessctl_connectivity_probe; HostessCompanion.Wpf.Tests",
            RequiresElevation: true,
            MutatesHost: true),
        new(
            "wpf.connectivity.firewall.verify",
            "Verify firewall rule",
            "VerifyFirewallRuleCommand",
            "$FirewallVerify = 'target\\connectivity-probe\\wpf-firewall-rule-verify.json'; " +
            HostessCtl + "connectivity-probe windows-firewall-rule --action verify --rule-profile '<rule-profile>' --out $FirewallVerify",
            "rusty.quest.connectivity_windows_firewall_rule.v1",
            "Hostess",
            "tools.test_hostessctl_connectivity_probe; HostessCompanion.Wpf.Tests"),
        new(
            "wpf.connectivity.verify",
            "Verify connectivity",
            "VerifyConnectivityCommand",
            "$ConnectivityReport = 'target\\connectivity-probe\\wpf-connectivity-verify.json'; " +
            "$StreamCapability = 'target\\connectivity-probe\\wpf-connectivity-verify.stream-capability.json'; " +
            "$ProbeId = '<QCL-010-or-QCL-080>'; " +
            "$Adb = '<adb>'; " +
            "$QuestSerial = '<quest-serial>'; " +
            "$HostessCompanionWpfExe = '<HostessCompanion.Wpf.exe>'; " +
            "$TcpEchoPort = 18766; " +
            "$UdpPort = 18767; " +
            "if ($ProbeId -eq 'QCL-080') { " +
            HostessCtl + "connectivity-probe run --mode live --probe-id QCL-080 --out $ConnectivityReport --adb $Adb --serial $QuestSerial --udp-port $UdpPort --udp-sender-source makepad-runtime --udp-listener-helper $HostessCompanionWpfExe; " +
            HostessCtl + "connectivity-probe stream-capability --input $ConnectivityReport --out $StreamCapability } " +
            "else { " +
            HostessCtl + "connectivity-probe run --mode live --probe-id QCL-010 --out $ConnectivityReport --adb $Adb --serial $QuestSerial --tcp-echo-port $TcpEchoPort }",
            "rusty.hostess.connectivity_probe.v1; rusty.quest.device_link.stream_capability.v1",
            "Hostess / Rusty Quest",
            "tools.test_hostessctl_connectivity_probe; tools.test_hostessctl_device_link_report; HostessCompanion.Wpf.Tests",
            RequiresQuestLease: true,
            MutatesDevice: true),
        new(
            "wpf.connectivity.suite",
            "Run connectivity suite",
            "RunConnectivitySuiteCommand",
            "$ConnectivitySuite = 'target\\connectivity-probe\\wpf-connectivity-suite.json'; " +
            "$ConnectivitySuiteArtifacts = 'target\\connectivity-probe\\wpf-connectivity-suite-artifacts'; " +
            "$HostessCompanionWpfExe = '<HostessCompanion.Wpf.exe>'; " +
            "$Adb = '<adb>'; " +
            "$QuestSerial = '<quest-serial>'; " +
            HostessCtl + "connectivity-probe run-suite --mode fixture --suite-id wpf-connectivity-suite --out $ConnectivitySuite --artifact-dir $ConnectivitySuiteArtifacts --listener-program $HostessCompanionWpfExe --listener-protocol '<TCP-or-UDP>' --listener-port '<port>' --adb $Adb --serial $QuestSerial",
            "rusty.quest.device_link.install_environment_suite_run.v1",
            "Hostess",
            "tools.test_hostessctl_connectivity_suite; HostessCompanion.Wpf.Tests"),
        new(
            "wpf.connectivity.protocol_matrix",
            "Build protocol matrix",
            "RunProtocolMatrixCommand",
            ProtocolMatrixCliRoute,
            "rusty.quest.device_link.protocol_evidence_matrix.v1; rusty.quest.connectivity_topology_probe.v1; rusty.hostess.direct_wifi_product_media_acceptance_plan.v1; rusty.hostess.companion.report_projection.v1; rusty.hostess.companion.transport_gate_report.v1",
            "Hostess / Rusty Quest / Manifold",
            "tools.test_hostessctl_protocol_evidence_matrix; tools.test_hostessctl_companion_report_projection; HostessCompanion.Wpf.Tests",
            RequiresQuestLease: true,
            MutatesHost: true,
            MutatesDevice: true),
        new(
            "wpf.connectivity.firewall.remove",
            "Remove firewall rule",
            "RemoveFirewallRuleCommand",
            "$FirewallRemove = 'target\\connectivity-probe\\wpf-firewall-rule-remove.json'; " +
            "$AdminHandoffScript = 'target\\connectivity-probe\\wpf-firewall-rule-remove.admin-handoff.ps1'; " +
            "$VerifyReport = 'target\\connectivity-probe\\wpf-firewall-rule-remove.verify.json'; " +
            HostessCtl + "connectivity-probe windows-firewall-rule --action remove --rule-profile '<rule-profile>' --out $FirewallRemove --handoff-script-out $AdminHandoffScript --handoff-verify-out $VerifyReport",
            "rusty.quest.connectivity_windows_firewall_rule.v1",
            "Hostess",
            "tools.test_hostessctl_connectivity_probe; HostessCompanion.Wpf.Tests",
            RequiresElevation: true,
            MutatesHost: true),
    ];
}
