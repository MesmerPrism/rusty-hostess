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
        "$PromotedTopologyReport = '<promoted-qcl040-or-qcl041-topology-report>'; " +
        "$ManifoldWebSocketRoute = '<manifold-stream-websocket-route>'; " +
        "$ManifoldWebSocketEvidence = '<manifold-stream-websocket-evidence>'; " +
        "$TopologyFixtureReports = '<topology-fixture-reports>'; " +
        "$Adb = '<adb>'; " +
        "$QuestSerial = '<quest-serial>'; " +
        "$Qcl040Preflight = '<qcl040-live-wifi-direct-preflight>'; " +
        "$Qcl041Preflight = '<qcl041-live-wifi-direct-preflight>'; " +
        "$LifecycleReport = '<wifi-direct-lifecycle-report>'; " +
        "$Qcl040LifecyclePlan = 'target\\connectivity-probe\\qcl040-wifi-direct-lifecycle-plan.json'; " +
        "$Qcl041LifecyclePlan = 'target\\connectivity-probe\\qcl041-wifi-direct-lifecycle-plan.json'; " +
        "$Qcl040LifecycleTemplate = 'target\\connectivity-probe\\qcl040-wifi-direct-lifecycle-template.json'; " +
        "$Qcl041LifecycleTemplate = 'target\\connectivity-probe\\qcl041-wifi-direct-lifecycle-template.json'; " +
        "$Qcl040LifecycleReport = 'target\\connectivity-probe\\qcl040-live-wifi-direct-lifecycle.json'; " +
        "$Qcl041LifecycleReport = 'target\\connectivity-probe\\qcl041-live-wifi-direct-lifecycle.json'; " +
        "$SuiteRun = '<suite-run>'; " +
        "$LatestArtifactDir = 'target\\connectivity-probe'; " +
        "$LatestDeviceLinkDir = 'target\\companion-session'; " +
        "$LatestStreamCapabilityDir = 'target\\connectivity-probe'; " +
        "$TopologyFixtureInputs = @('--input', '<qcl020-topology-report>', '--input', '<qcl030-topology-report>', '--input', '<qcl040-topology-report>', '--input', '<qcl041-topology-report>'); " +
        "$LatestProbeArgs = @('--latest-probe-id', 'QCL-000', '--latest-probe-id', 'QCL-010', '--latest-probe-id', 'QCL-011', '--latest-probe-id', 'QCL-020', '--latest-probe-id', 'QCL-030', '--latest-probe-id', 'QCL-040', '--latest-probe-id', 'QCL-041', '--latest-probe-id', 'QCL-050', '--latest-probe-id', 'QCL-051', '--latest-probe-id', 'QCL-080', '--latest-probe-id', 'QCL-081', '--latest-probe-id', 'QCL-082', '--latest-probe-id', 'QCL-083', '--latest-probe-id', 'QCL-084', '--latest-probe-id', 'QCL-079'); " +
        "$ProtocolMatrix = '<protocol-matrix>'; " +
        "$Projection = '<projection>'; " +
        "$TransportGates = '<transport-gates>'; " +
        "python $HostessCtl connectivity-probe qcl082-product-media-plan --out $ProductMediaPlan --promoted-topology-report $PromotedTopologyReport --firewall-report $FirewallVerify --adb $Adb --serial $QuestSerial; " +
        "python $HostessCtl connectivity-probe direct-wifi-product-media-plan --out $DirectWifiProductMediaPlan --qcl040-topology-report $Qcl040LifecycleReport --qcl041-topology-report $Qcl041LifecycleReport --promoted-topology-report $PromotedTopologyReport --firewall-report $FirewallVerify --qcl082-report target\\connectivity-probe\\qcl082-rmanvid1-receiver-capture.json --adb $Adb --serial $QuestSerial; " +
        "python $HostessCtl connectivity-probe run --probe-id QCL-082 --media-stream-session-plan $MediaStreamSessionPlan; " +
        "python $HostessCtl emit-bridge-command-request --bridge-command command.media_stream.start_source --request-id request.hostess.qcl082.media_stream.start_source --evidence-id evidence.hostess.qcl082.media_stream.start_source --route-id bridge_route.command.websocket.applied --required-stage sent --required-stage transport_ok --required-stage authority_accepted --out $StartSourceRequest; " +
        "python $HostessCtl run-bridge-command-live-android --input $StartSourceRequest --out $StartSourceBridgeEvidence --execution-out $RuntimeStatus --validation-out $StartSourceValidation --adb $Adb --serial $QuestSerial; " +
        "python $HostessCtl connectivity-probe run --probe-id QCL-082 --media-stream-runtime-status $RuntimeStatus; " +
        "python $HostessCtl connectivity-probe windows-firewall-rule --action verify --rule-profile qcl-082-rmanvid1-media --program $HostessCompanionWpfExe --out $FirewallVerify; " +
        "python $HostessCtl connectivity-probe qcl082-product-media-live-session --bridge-command command.media_stream.start_source --start-source-request-out $StartSourceRequest --bridge-evidence-out $StartSourceBridgeEvidence --execution-out $RuntimeStatus --validation-out $StartSourceValidation --logcat-out $StartSourceLogcat --capture-out $Rmanvid1Capture --sidecar-out $ReceiverSidecar --topology-report $PromotedTopologyReport --firewall-report $FirewallVerify --adb $Adb --serial $QuestSerial --out $ReceiverResult; " +
        "python $HostessCtl connectivity-probe rmanvid1-receiver-capture --capture-out $Rmanvid1Capture --sidecar-out $ReceiverSidecar --runtime-status $RuntimeStatus --topology-report $PromotedTopologyReport --firewall-report $FirewallVerify --out $ReceiverResult; " +
        "python $HostessCtl connectivity-probe run --probe-id QCL-082 --media-stream-receiver-result $ReceiverResult; " +
        "python $HostessCtl connectivity-probe run --probe-id QCL-079 --websocket-source host-loopback; " +
        "python $HostessCtl connectivity-probe run --probe-id QCL-079 --websocket-source broker-owned-websocket --websocket-route-descriptor $ManifoldWebSocketRoute --websocket-route-evidence $ManifoldWebSocketEvidence; " +
        "python $HostessCtl connectivity-probe run-suite --out $SuiteRun; " +
        "python $HostessCtl connectivity-probe run --mode fixture --probe-id QCL-020 --fixture-profile qcl-020-wifi-adb-session-pass; " +
        "python $HostessCtl connectivity-probe run --mode fixture --probe-id QCL-030 --fixture-profile qcl-030-local-only-hotspot-started; " +
        "python $HostessCtl connectivity-probe run --mode fixture --probe-id QCL-040 --fixture-profile qcl-040-wifi-direct-phone-peer-pass; " +
        "python $HostessCtl connectivity-probe run --mode fixture --probe-id QCL-041 --fixture-profile qcl-041-wifi-direct-windows-peer-pass; " +
        "python $HostessCtl connectivity-probe wifi-direct-lifecycle-plan --probe-id QCL-040 --out $Qcl040LifecyclePlan --adb $Adb --serial $QuestSerial; " +
        "python $HostessCtl connectivity-probe wifi-direct-lifecycle-plan --probe-id QCL-041 --out $Qcl041LifecyclePlan --adb $Adb --serial $QuestSerial; " +
        "python $HostessCtl connectivity-probe run --mode live --probe-id QCL-040 --adb $Adb --serial $QuestSerial --out $Qcl040Preflight; " +
        "python $HostessCtl connectivity-probe run --mode live --probe-id QCL-041 --adb $Adb --serial $QuestSerial --out $Qcl041Preflight; " +
        "python $HostessCtl connectivity-probe wifi-direct-lifecycle-template --probe-id QCL-040 --out $Qcl040LifecycleTemplate; " +
        "python $HostessCtl connectivity-probe wifi-direct-lifecycle-template --probe-id QCL-041 --out $Qcl041LifecycleTemplate; " +
        "python $HostessCtl connectivity-probe run --mode fixture --probe-id QCL-040 --wifi-direct-lifecycle-report $LifecycleReport --out $Qcl040LifecycleReport --fail-on-error; " +
        "python $HostessCtl connectivity-probe run --mode fixture --probe-id QCL-041 --wifi-direct-lifecycle-report $LifecycleReport --out $Qcl041LifecycleReport --fail-on-error; " +
        "python $HostessCtl connectivity-probe protocol-matrix --suite-run $SuiteRun @TopologyFixtureInputs --latest-artifact-dir $LatestArtifactDir @LatestProbeArgs --latest-device-link-dir $LatestDeviceLinkDir --latest-stream-capability-dir $LatestStreamCapabilityDir --latest-stream-probe-id QCL-080 --out $ProtocolMatrix; " +
        "python $HostessCtl companion-report projection --protocol-matrix $ProtocolMatrix --include-protocol-matrix-inputs --suite-run $SuiteRun --out $Projection; " +
        "python $HostessCtl companion-report transport-gates --projection $Projection --out $TransportGates --fail-on-pending";

    public static IReadOnlyList<OperatorActionDescriptor> All { get; } =
    [
        new(
            "wpf.readiness.refresh",
            "Refresh readiness and catalog",
            "RefreshCommand",
            HostessCtl + "companion-readiness; " + HostessCtl + "companion-catalog",
            "rusty.hostess.companion.readiness_report.v1; rusty.hostess.companion.catalog.v1",
            "Hostess",
            "tools.test_hostessctl_companion_readiness; tools.test_hostessctl_companion_catalog; HostessCompanion.Wpf.Tests"),
        new(
            "wpf.session.run",
            "Run companion session",
            "RunSessionCommand",
            HostessCtl + "companion-session run --frontend wpf --profile hostess-makepad-quest " +
            "--wait-seconds 30 --fallback-wait-seconds 30 --authority-wait-seconds 30 " +
            "--broker-process-wait-seconds 20 --makepad-process-wait-seconds 20 " +
            "--socket-wait-seconds 20 --launch-settle-seconds 8 " +
            "--runtime-subscriber-retry-count 8 --runtime-subscriber-retry-wait-seconds 2",
            "rusty.hostess.companion.session.v1; rusty.quest.device_link.v1",
            "Hostess",
            "tools.test_hostessctl_companion_session; HostessCompanion.Wpf.Tests"),
        new(
            "wpf.session.history",
            "Load session history",
            "LoadSessionHistoryCommand",
            HostessCtl + "companion-session history",
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
            "$PrimaryEvidence = '<broker-stream-evidence>'; $FallbackEvidence = '<app-private-evidence>'; " +
            HostessCtl + "run-bridge-command-live-android --out $PrimaryEvidence; " +
            "if ($LASTEXITCODE -ne 0) { " + HostessCtl + "run-bridge-command-android --out $FallbackEvidence }",
            "rusty.hostess.bridge_command.live_android_execution_evidence.v1",
            "Hostess / Manifold / Rusty Quest",
            "tools.test_hostessctl_bridge_command_live_android; HostessCompanion.Wpf.Tests"),
        new(
            "wpf.connectivity.firewall.plan",
            "Plan firewall rule",
            "PlanFirewallRuleCommand",
            HostessCtl + "connectivity-probe windows-firewall-rule --action plan --rule-profile '<rule-profile>'",
            "rusty.quest.connectivity_windows_firewall_rule.v1",
            "Hostess",
            "tools.test_hostessctl_connectivity_probe; HostessCompanion.Wpf.Tests"),
        new(
            "wpf.connectivity.firewall.apply",
            "Apply firewall rule",
            "ApplyFirewallRuleCommand",
            "$AdminHandoffScript = '<admin.ps1>'; $VerifyReport = '<verify-report>'; " + HostessCtl + "connectivity-probe windows-firewall-rule --action apply --rule-profile '<rule-profile>' --handoff-script-out $AdminHandoffScript --handoff-verify-out $VerifyReport",
            "rusty.quest.connectivity_windows_firewall_rule.v1",
            "Hostess",
            "tools.test_hostessctl_connectivity_probe; HostessCompanion.Wpf.Tests"),
        new(
            "wpf.connectivity.firewall.verify",
            "Verify firewall rule",
            "VerifyFirewallRuleCommand",
            HostessCtl + "connectivity-probe windows-firewall-rule --action verify --rule-profile '<rule-profile>'",
            "rusty.quest.connectivity_windows_firewall_rule.v1",
            "Hostess",
            "tools.test_hostessctl_connectivity_probe; HostessCompanion.Wpf.Tests"),
        new(
            "wpf.connectivity.verify",
            "Verify connectivity",
            "VerifyConnectivityCommand",
            HostessCtl + "connectivity-probe run --probe-id '<QCL-010-or-QCL-080>'; " + HostessCtl + "connectivity-probe stream-capability",
            "rusty.hostess.connectivity_probe.v1; rusty.quest.device_link.stream_capability.v1",
            "Hostess / Rusty Quest",
            "tools.test_hostessctl_connectivity_probe; tools.test_hostessctl_device_link_report; HostessCompanion.Wpf.Tests"),
        new(
            "wpf.connectivity.suite",
            "Run connectivity suite",
            "RunConnectivitySuiteCommand",
            HostessCtl + "connectivity-probe run-suite",
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
            "tools.test_hostessctl_protocol_evidence_matrix; tools.test_hostessctl_companion_report_projection; HostessCompanion.Wpf.Tests"),
        new(
            "wpf.connectivity.firewall.remove",
            "Remove firewall rule",
            "RemoveFirewallRuleCommand",
            "$AdminHandoffScript = '<admin.ps1>'; $VerifyReport = '<verify-report>'; " + HostessCtl + "connectivity-probe windows-firewall-rule --action remove --rule-profile '<rule-profile>' --handoff-script-out $AdminHandoffScript --handoff-verify-out $VerifyReport",
            "rusty.quest.connectivity_windows_firewall_rule.v1",
            "Hostess",
            "tools.test_hostessctl_connectivity_probe; HostessCompanion.Wpf.Tests"),
    ];
}
