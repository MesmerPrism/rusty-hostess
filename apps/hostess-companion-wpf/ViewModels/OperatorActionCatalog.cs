namespace HostessCompanion.Wpf.ViewModels;

public static class OperatorActionCatalog
{
    public static IReadOnlyList<OperatorActionDescriptor> All { get; } =
    [
        new(
            "wpf.readiness.refresh",
            "Refresh readiness and catalog",
            "RefreshCommand",
            "companion-readiness; companion-catalog",
            "rusty.hostess.companion.readiness_report.v1; rusty.hostess.companion.catalog.v1",
            "Hostess",
            "tools.test_hostessctl_companion_readiness; tools.test_hostessctl_companion_catalog; HostessCompanion.Wpf.Tests"),
        new(
            "wpf.session.run",
            "Run companion session",
            "RunSessionCommand",
            "companion-session run --frontend wpf --profile hostess-makepad-quest " +
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
            "companion-session history",
            "rusty.hostess.companion.session_history.v1",
            "Hostess",
            "tools.test_hostessctl_companion_session; HostessCompanion.Wpf.Tests"),
        new(
            "wpf.session.load_selected",
            "Load selected session",
            "LoadSelectedSessionCommand",
            "companion-session history -> rusty.hostess.companion.session.v1 report_path",
            "rusty.hostess.companion.session.v1",
            "Hostess",
            "tools.test_hostessctl_companion_session; HostessCompanion.Wpf.Tests"),
        new(
            "wpf.command.safe_probe",
            "Run safe bridge probe",
            "RunProbeCommand",
            "run-bridge-command-live-android; run-bridge-command-android fallback",
            "rusty.hostess.bridge_command.live_android_execution_evidence.v1",
            "Hostess / Manifold / Rusty Quest",
            "tools.test_hostessctl_bridge_command_live_android; HostessCompanion.Wpf.Tests"),
        new(
            "wpf.connectivity.firewall.plan",
            "Plan firewall rule",
            "PlanFirewallRuleCommand",
            "connectivity-probe windows-firewall-rule --action plan",
            "rusty.quest.connectivity_windows_firewall_rule.v1",
            "Hostess",
            "tools.test_hostessctl_connectivity_probe; HostessCompanion.Wpf.Tests"),
        new(
            "wpf.connectivity.firewall.apply",
            "Apply firewall rule",
            "ApplyFirewallRuleCommand",
            "connectivity-probe windows-firewall-rule --action apply",
            "rusty.quest.connectivity_windows_firewall_rule.v1",
            "Hostess",
            "tools.test_hostessctl_connectivity_probe; HostessCompanion.Wpf.Tests"),
        new(
            "wpf.connectivity.firewall.verify",
            "Verify firewall rule",
            "VerifyFirewallRuleCommand",
            "connectivity-probe windows-firewall-rule --action verify",
            "rusty.quest.connectivity_windows_firewall_rule.v1",
            "Hostess",
            "tools.test_hostessctl_connectivity_probe; HostessCompanion.Wpf.Tests"),
        new(
            "wpf.connectivity.verify",
            "Verify connectivity",
            "VerifyConnectivityCommand",
            "connectivity-probe run --probe-id QCL-010|QCL-080; connectivity-probe stream-capability",
            "rusty.hostess.connectivity_probe.v1; rusty.quest.device_link.stream_capability.v1",
            "Hostess / Rusty Quest",
            "tools.test_hostessctl_connectivity_probe; tools.test_hostessctl_device_link_report; HostessCompanion.Wpf.Tests"),
        new(
            "wpf.connectivity.suite",
            "Run connectivity suite",
            "RunConnectivitySuiteCommand",
            "connectivity-probe run-suite",
            "rusty.quest.device_link.install_environment_suite_run.v1",
            "Hostess",
            "tools.test_hostessctl_connectivity_suite; HostessCompanion.Wpf.Tests"),
        new(
            "wpf.connectivity.protocol_matrix",
            "Build protocol matrix",
            "RunProtocolMatrixCommand",
            "connectivity-probe run --probe-id QCL-082 --media-stream-session-plan <rusty-quest-media-stream-plan>; connectivity-probe run --probe-id QCL-082 --media-stream-runtime-status <broker-media-stream-runtime-status>; connectivity-probe rmanvid1-receiver-capture --capture-out <rmanvid1-capture> --sidecar-out <receiver-sidecar> --runtime-status <broker-media-stream-runtime-status>; connectivity-probe run --probe-id QCL-082 --media-stream-rmanvid1-capture <rmanvid1-capture> --media-stream-receiver-sidecar <receiver-sidecar> --media-stream-runtime-status <broker-media-stream-runtime-status>; connectivity-probe run-suite; connectivity-probe protocol-matrix --suite-run --latest-artifact-dir --latest-probe-id QCL-050|QCL-051|QCL-080|QCL-081|QCL-082|QCL-083|QCL-084 --latest-device-link-dir --latest-stream-capability-dir --latest-stream-probe-id QCL-080; companion-report projection --protocol-matrix --include-protocol-matrix-inputs --suite-run",
            "rusty.quest.device_link.protocol_evidence_matrix.v1; rusty.quest.connectivity_topology_probe.v1; rusty.hostess.companion.report_projection.v1",
            "Hostess / Rusty Quest / Manifold",
            "tools.test_hostessctl_protocol_evidence_matrix; tools.test_hostessctl_companion_report_projection; HostessCompanion.Wpf.Tests"),
        new(
            "wpf.connectivity.firewall.remove",
            "Remove firewall rule",
            "RemoveFirewallRuleCommand",
            "connectivity-probe windows-firewall-rule --action remove",
            "rusty.quest.connectivity_windows_firewall_rule.v1",
            "Hostess",
            "tools.test_hostessctl_connectivity_probe; HostessCompanion.Wpf.Tests"),
    ];
}
