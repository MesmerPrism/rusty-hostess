using System.Diagnostics;
using System.Globalization;
using System.Reflection;
using System.Text.RegularExpressions;
using System.Text.Json;
using HostessCompanion.Wpf.Models;
using HostessCompanion.Wpf.Services;
using HostessCompanion.Wpf.ViewModels;

static partial class WpfCompanionTests
{
    public static void TransportGateRowsExposeNextActions()
    {
        var report = TransportGateReportFixtures.PendingWithNextActions();
    
        var serializedReport = JsonSerializer.Serialize(report);
        Assert(serializedReport.Contains("\"data_protocols\"", StringComparison.Ordinal),
            "transport gate report JSON must preserve data_protocols");
        Assert(serializedReport.Contains("\"completion_blockers\"", StringComparison.Ordinal),
            "transport gate report JSON must preserve completion_blockers");
        var roundTripped = JsonSerializer.Deserialize<CompanionTransportGateReport>(serializedReport)
            ?? throw new InvalidOperationException("transport gate report round-trip failed");
        Assert(roundTripped.DataProtocols.RequiredPromotedCount == 4,
            "transport gate report model must deserialize data_protocol counters");
        Assert(roundTripped.Summary.CompletionBlockers.Contains("protocol_matrix.required_data_protocols"),
            "transport gate report model must deserialize completion blockers");
    
        var rows = ConnectivityRows.ForTransportGateReport(report);
    
        Assert(rows.Any(row => row.Name == "hostess.companion_transport_gates" && row.Status == "warn"),
            "transport gate report summary row must stay visible");
        Assert(rows.Any(row =>
                row.Name == "hostess.companion_transport_gates"
                && row.Evidence.Contains("data_protocols_promoted=False", StringComparison.Ordinal)
                && row.Evidence.Contains("complete=False", StringComparison.Ordinal)
                && row.Notes.Contains("target/companion-report/transport-gates.json", StringComparison.Ordinal)
                && row.Notes.Contains("validation_report=target/companion-report/transport-gates.validation-report.json", StringComparison.Ordinal)
                && row.Notes.Contains("completion_blockers=protocol_matrix.required_data_protocols,transport.general_websocket_capability,transport.direct_wifi_live_topology,transport.product_tcp_media_over_direct_wifi,transport.product_tcp_media_listener_firewall", StringComparison.Ordinal)),
            "transport gate summary row must expose report artifacts and strict protocol-plus-transport completion blockers");
        Assert(rows.Any(row =>
                row.Name == "transport_gates.validation_sidecar"
                && row.Status == "warn"
                && row.Evidence.Contains("status=pass", StringComparison.Ordinal)
                && row.Evidence.Contains("errors=0", StringComparison.Ordinal)
                && row.Evidence.Contains("warnings=5", StringComparison.Ordinal)
                && row.Evidence.Contains("remaining_gates=4", StringComparison.Ordinal)
                && row.Evidence.Contains("data_protocols_promoted=False", StringComparison.Ordinal)
                && row.Evidence.Contains("complete=False", StringComparison.Ordinal)
                && row.Notes.Contains("validation_report=target/companion-report/transport-gates.validation-report.json", StringComparison.Ordinal)
                && row.Notes.Contains("source_projection=target/companion-report/projection.json", StringComparison.Ordinal)
                && row.IssueCodes.Contains("hostess.issue.transport_gates.required_data_protocols_not_promoted")
                && row.IssueCodes.Contains("hostess.issue.transport_gates.gate_pending")),
            "transport gate validation sidecar row must expose Hostess validation status and issue codes");
        Assert(rows.Any(row =>
                row.Name == "transport_gates.data_protocols"
                && row.Status == "warn"
                && row.Evidence.Contains("protocol_matrix_present=True", StringComparison.Ordinal)
                && row.Evidence.Contains("all_required_data_protocols_promoted=False", StringComparison.Ordinal)
                && row.Evidence.Contains("required=4/5", StringComparison.Ordinal)
                && row.Notes.Contains("source=target/connectivity-probe/protocol-matrix.json", StringComparison.Ordinal)
                && row.Notes.Contains("completion_blockers=protocol_matrix.required_data_protocols", StringComparison.Ordinal)
                && row.IssueCodes.Contains("hostess.issue.transport_gates.required_data_protocols_not_promoted")),
            "transport gate rows must preserve Hostess data-protocol completion evidence");
        Assert(rows.Any(row =>
                row.Name == "transport_gates.operator_next_actions"
                && row.Evidence.Contains("shell=powershell", StringComparison.Ordinal)),
            "transport gate rows must include the operator next-action summary");
        Assert(rows.Any(row =>
                row.Name == "transport.general_websocket_capability.run_qcl079_host_loopback_websocket"
                && row.Notes.Contains("requires_quest_lease=False", StringComparison.Ordinal)
                && row.Notes.Contains("requires_adb_server_lifecycle_lease=False", StringComparison.Ordinal)
                && row.Notes.Contains("authority_owner=tools.hostessctl.connectivity_websocket", StringComparison.Ordinal)
                && row.Notes.Contains("clears_gate=False", StringComparison.Ordinal)
                && row.Evidence.Contains("--probe-id QCL-079", StringComparison.Ordinal)
                && row.Evidence.Contains("--websocket-source host-loopback", StringComparison.Ordinal)),
            "generic WebSocket host-loopback action must stay candidate-only and CLI-equivalent");
        Assert(rows.Any(row =>
                row.Name == "transport.general_websocket_capability.run_qcl079_broker_owned_websocket"
                && row.Notes.Contains("requires_elevation=False", StringComparison.Ordinal)
                && row.Notes.Contains("requires_quest_lease=False", StringComparison.Ordinal)
                && row.Notes.Contains("mutates_host=False", StringComparison.Ordinal)
                && row.Notes.Contains("mutates_device=False", StringComparison.Ordinal)
                && row.Notes.Contains("clears_gate=True", StringComparison.Ordinal)
                && row.Notes.Contains("acceptance_artifacts=target\\connectivity-probe\\qcl079-live-broker-owned-websocket.json", StringComparison.Ordinal)
                && row.Evidence.Contains("--websocket-source broker-owned-websocket", StringComparison.Ordinal)
                && row.Evidence.Contains("--websocket-route-descriptor '<manifold-stream-websocket-route>'", StringComparison.Ordinal)
                && row.Evidence.Contains("--websocket-route-evidence '<manifold-stream-websocket-evidence>'", StringComparison.Ordinal)),
            "generic WebSocket gate must render the broker-owned QCL-079 route that can clear it");
        Assert(rows.Any(row =>
                row.Name == "transport.direct_wifi_live_topology.run_qcl041_live_wifi_direct_preflight"
                && row.Notes.Contains("requires_quest_lease=True", StringComparison.Ordinal)
                && row.Notes.Contains("requires_adb_server_lifecycle_lease=False", StringComparison.Ordinal)
                && row.Notes.Contains("lease_resource=quest:<quest-serial>", StringComparison.Ordinal)
                && row.Notes.Contains("lease_release=& 'S:\\Work\\agent-bureau\\scripts\\agent-board.ps1' release '<quest-lease-id>' --result done", StringComparison.Ordinal)),
            "direct Wi-Fi next action must show Quest lease resource, release command, and non-lifecycle ADB policy");
        Assert(rows.Any(row =>
                row.Name == "transport.direct_wifi_live_topology.plan_qcl041_wifi_direct_lifecycle"
                && row.Notes.Contains("requires_quest_lease=False", StringComparison.Ordinal)
                && row.Notes.Contains("authority_owner=tools.hostessctl.connectivity_topology_lifecycle_plan", StringComparison.Ordinal)
                && row.Notes.Contains("acceptance_artifacts=target\\connectivity-probe\\qcl041-wifi-direct-lifecycle-plan.json", StringComparison.Ordinal)
                && row.Evidence.Contains("wifi-direct-lifecycle-plan", StringComparison.Ordinal)),
            "direct Wi-Fi lifecycle plan must be visible as a non-mutating CLI-equivalent WPF action");
        Assert(rows.Any(row =>
                row.Name == "transport.direct_wifi_live_topology.write_direct_wifi_product_media_acceptance_plan"
                && row.Notes.Contains("requires_quest_lease=False", StringComparison.Ordinal)
                && row.Notes.Contains("authority_owner=tools.hostessctl.connectivity_direct_wifi_product_media_plan", StringComparison.Ordinal)
                && row.Notes.Contains("acceptance_artifacts=target\\connectivity-probe\\direct-wifi-product-media-acceptance-plan.json", StringComparison.Ordinal)
                && row.Evidence.Contains("direct-wifi-product-media-plan", StringComparison.Ordinal)
                && row.Evidence.Contains("--qcl040-lifecycle-report '<qcl040-live-wifi-direct-lifecycle-source>'", StringComparison.Ordinal)
                && row.Evidence.Contains("--qcl040-topology-report target\\connectivity-probe\\qcl040-live-wifi-direct-lifecycle.json", StringComparison.Ordinal)
                && row.Evidence.Contains("--promoted-topology-report '<promoted-qcl040-or-qcl041-topology-report>'", StringComparison.Ordinal)
                && row.Evidence.Contains("--qcl082-report", StringComparison.Ordinal)
                && row.Evidence.Contains("--quest-lease-id '<quest-lease-id>'", StringComparison.Ordinal)),
            "direct Wi-Fi gate must render the combined read-only product-media acceptance plan");
        Assert(rows.Any(row =>
                row.Name == "transport.direct_wifi_live_topology.normalize_qcl040_wifi_direct_lifecycle_report"
                && row.Notes.Contains("requires_quest_lease=False", StringComparison.Ordinal)
                && row.Notes.Contains("authority_owner=tools.hostessctl.connectivity_topology_lifecycle", StringComparison.Ordinal)
                && row.Notes.Contains("acceptance_artifacts=target\\connectivity-probe\\qcl040-live-wifi-direct-lifecycle.json", StringComparison.Ordinal)
                && row.Notes.Contains("clears_gate=True", StringComparison.Ordinal)
                && row.Evidence.Contains("--probe-id QCL-040", StringComparison.Ordinal)
                && row.Evidence.Contains("--wifi-direct-lifecycle-report '<wifi-direct-lifecycle-report>'", StringComparison.Ordinal)),
            "QCL-040 lifecycle normalizer must be visible as a CLI-equivalent WPF action");
        Assert(rows.Any(row =>
                row.Name == "transport.direct_wifi_live_topology.normalize_qcl041_wifi_direct_lifecycle_report"
                && row.Notes.Contains("requires_quest_lease=False", StringComparison.Ordinal)
                && row.Notes.Contains("authority_owner=tools.hostessctl.connectivity_topology_lifecycle", StringComparison.Ordinal)
                && row.Notes.Contains("acceptance_artifacts=target\\connectivity-probe\\qcl041-live-wifi-direct-lifecycle.json", StringComparison.Ordinal)
                && row.Notes.Contains("clears_gate=True", StringComparison.Ordinal)
                && row.Evidence.Contains("--probe-id QCL-041", StringComparison.Ordinal)
                && row.Evidence.Contains("--wifi-direct-lifecycle-report '<wifi-direct-lifecycle-report>'", StringComparison.Ordinal)),
            "QCL-041 lifecycle normalizer must be visible as a CLI-equivalent WPF action");
        Assert(rows.Any(row =>
                row.Name == "transport.product_tcp_media_over_direct_wifi.write_qcl082_product_media_direct_wifi_plan"
                && row.Notes.Contains("authority_owner=tools.hostessctl.connectivity_media_product_plan", StringComparison.Ordinal)
                && row.Notes.Contains("acceptance_artifacts=target\\connectivity-probe\\qcl082-product-media-direct-wifi-plan.json", StringComparison.Ordinal)
                && row.Evidence.Contains("qcl082-product-media-plan", StringComparison.Ordinal)
                && row.Evidence.Contains("--promoted-topology-report '<promoted-qcl040-or-qcl041-topology-report>'", StringComparison.Ordinal)
                && row.Evidence.Contains("--quest-lease-resource 'quest:<quest-serial>'", StringComparison.Ordinal)),
            "product media plan action must render the CLI-owned direct-Wi-Fi media plan artifact");
        Assert(rows.Any(row =>
                row.Name == "transport.product_tcp_media_over_direct_wifi.write_direct_wifi_product_media_acceptance_plan"
                && row.Notes.Contains("authority_owner=tools.hostessctl.connectivity_direct_wifi_product_media_plan", StringComparison.Ordinal)
                && row.Notes.Contains("acceptance_artifacts=target\\connectivity-probe\\direct-wifi-product-media-acceptance-plan.json", StringComparison.Ordinal)
                && row.Evidence.Contains("direct-wifi-product-media-plan", StringComparison.Ordinal)
                && row.Evidence.Contains("--firewall-report", StringComparison.Ordinal)
                && row.Evidence.Contains("--qcl041-lifecycle-report '<qcl041-live-wifi-direct-lifecycle-source>'", StringComparison.Ordinal)
                && row.Evidence.Contains("--quest-lease-resource 'quest:<quest-serial>'", StringComparison.Ordinal)),
            "product media gate must render the combined read-only direct-Wi-Fi acceptance plan");
        Assert(rows.Any(row =>
                row.Name == "transport.product_tcp_media_over_direct_wifi.write_qcl082_media_stream_start_source_request"
                && row.Notes.Contains("authority_owner=tools.hostessctl.bridge_command_routes", StringComparison.Ordinal)
                && row.Notes.Contains("acceptance_artifacts=target\\connectivity-probe\\media-stream-start-source.request.json", StringComparison.Ordinal)
                && row.Evidence.Contains("emit-bridge-command-request", StringComparison.Ordinal)
                && row.Evidence.Contains("--bridge-command command.media_stream.start_source", StringComparison.Ordinal)
                && row.Evidence.Contains("--required-stage authority_accepted", StringComparison.Ordinal)),
            "product media request action must render the inspectable bridge-command request artifact");
        Assert(rows.Any(row =>
                row.Name == "transport.product_tcp_media_over_direct_wifi.run_qcl082_media_stream_start_source"
                && row.Notes.Contains("authority_owner=tools.hostessctl.bridge_command_live_android_routes", StringComparison.Ordinal)
                && row.Notes.Contains("requires_quest_lease=True", StringComparison.Ordinal)
                && row.Notes.Contains("mutates_host=True", StringComparison.Ordinal)
                && row.Notes.Contains("mutates_device=True", StringComparison.Ordinal)
                && row.Notes.Contains("lease_resource=quest:<quest-serial>", StringComparison.Ordinal)
                && row.Evidence.Contains("run-bridge-command-live-android", StringComparison.Ordinal)
                && row.Evidence.Contains("--execution-out target\\connectivity-probe\\media-stream-start-source.live-android-execution.json", StringComparison.Ordinal)),
            "product media start_source action must show the leased live Android bridge route");
        Assert(rows.Any(row =>
                row.Name == "transport.product_tcp_media_over_direct_wifi.validate_qcl082_media_stream_runtime_status"
                && row.Notes.Contains("authority_owner=tools.hostessctl.connectivity_media", StringComparison.Ordinal)
                && row.Evidence.Contains("--media-stream-runtime-status target\\connectivity-probe\\media-stream-start-source.live-android-execution.json", StringComparison.Ordinal)),
            "product media runtime-status action must consume the live Android execution artifact");
        Assert(rows.Any(row =>
                row.Name == "transport.product_tcp_media_over_direct_wifi.run_qcl082_product_media_live_session"
                && row.Notes.Contains("authority_owner=tools.hostessctl.connectivity_media_receiver", StringComparison.Ordinal)
                && row.Notes.Contains("requires_quest_lease=True", StringComparison.Ordinal)
                && row.Notes.Contains("mutates_device=True", StringComparison.Ordinal)
                && row.Notes.Contains("acceptance_artifacts=target\\connectivity-probe\\media-stream-start-source.request.json,target\\connectivity-probe\\media-stream-start-source.bridge-evidence.json,target\\connectivity-probe\\media-stream-start-source.live-android-execution.json,target\\connectivity-probe\\media-stream-start-source.validation-report.json,target\\connectivity-probe\\media-stream.rmanvid1,target\\connectivity-probe\\media-stream-receiver-sidecar.json,target\\connectivity-probe\\media-stream-receiver-result.json", StringComparison.Ordinal)
                && row.Evidence.Contains("qcl082-product-media-live-session", StringComparison.Ordinal)
                && row.Evidence.Contains("--start-source-request-out target\\connectivity-probe\\media-stream-start-source.request.json", StringComparison.Ordinal)
                && row.Evidence.Contains("--logcat-out target\\connectivity-probe\\media-stream-start-source.logcat.txt", StringComparison.Ordinal)
                && row.Evidence.Contains("--bind-host 0.0.0.0", StringComparison.Ordinal)
                && row.Evidence.Contains("--preview-ffplay '<ffplay>'", StringComparison.Ordinal)
                && row.Evidence.Contains("--preview-window-title 'Rusty QCL-082 Camera2 direct-WiFi preview'", StringComparison.Ordinal)
                && row.Evidence.Contains("--capture-kind live_broker_stream", StringComparison.Ordinal)
                && row.Evidence.Contains("--quest-lease-id '<quest-lease-id>'", StringComparison.Ordinal)
                && row.Evidence.Contains("--quest-lease-reserved-before-live-steps", StringComparison.Ordinal)
                && row.Evidence.Contains("--out target\\connectivity-probe\\media-stream-receiver-result.json", StringComparison.Ordinal)
                && row.Evidence.Contains("--fail-on-error", StringComparison.Ordinal)),
            "product media live session action must show the orchestrated receiver-plus-command route");
        Assert(rows.Any(row =>
                row.Name == "transport.product_tcp_media_over_direct_wifi.capture_rmanvid1_over_promoted_direct_wifi"
                && row.Notes.Contains("authority_owner=tools.hostessctl.connectivity_media_receiver", StringComparison.Ordinal)
                && row.Notes.Contains("requires_quest_lease=True", StringComparison.Ordinal)
                && row.Notes.Contains("mutates_device=True", StringComparison.Ordinal)
                && row.Notes.Contains("depends_on=transport.direct_wifi_live_topology,transport.product_tcp_media_listener_firewall", StringComparison.Ordinal)
                && row.Notes.Contains("acceptance_artifacts=target\\connectivity-probe\\media-stream.rmanvid1,target\\connectivity-probe\\media-stream-receiver-sidecar.json,target\\connectivity-probe\\media-stream-receiver-result.json", StringComparison.Ordinal)
                && row.Evidence.Contains("--capture-out target\\connectivity-probe\\media-stream.rmanvid1", StringComparison.Ordinal)
                && row.Evidence.Contains("--sidecar-out target\\connectivity-probe\\media-stream-receiver-sidecar.json", StringComparison.Ordinal)
                && row.Evidence.Contains("--runtime-status target\\connectivity-probe\\media-stream-start-source.live-android-execution.json", StringComparison.Ordinal)
                && row.Evidence.Contains("--preview-ffplay '<ffplay>'", StringComparison.Ordinal)
                && row.Evidence.Contains("--preview-window-title 'Rusty QCL-082 Camera2 direct-WiFi preview'", StringComparison.Ordinal)
                && row.Evidence.Contains("--quest-lease-resource 'quest:<quest-serial>'", StringComparison.Ordinal)
                && row.Evidence.Contains("--quest-lease-reserved-before-live-steps", StringComparison.Ordinal)
                && row.Evidence.Contains("--out target\\connectivity-probe\\media-stream-receiver-result.json", StringComparison.Ordinal)
                && row.Evidence.Contains("--fail-on-error", StringComparison.Ordinal)),
            "product media next action must show dependency and acceptance-artifact evidence");
        Assert(rows.Any(row =>
                row.Name == "transport.product_tcp_media_over_direct_wifi.promote_qcl082_rmanvid1_capture"
                && row.Notes.Contains("authority_owner=tools.hostessctl.connectivity_probe", StringComparison.Ordinal)
                && row.Notes.Contains("clears_gate=True", StringComparison.Ordinal)
                && row.Evidence.Contains("--media-stream-receiver-result target\\connectivity-probe\\media-stream-receiver-result.json", StringComparison.Ordinal)),
            "product media promotion action must render the QCL-082 fold-in route");
        Assert(rows.Any(row =>
                row.Name == "transport.product_tcp_media_listener_firewall.verify_qcl082_product_firewall_rule"
                && row.Notes.Contains("requires_elevation=False", StringComparison.Ordinal)
                && row.Notes.Contains("mutates_host=False", StringComparison.Ordinal)
                && row.Evidence.Contains("--rule-profile qcl-082-rmanvid1-media", StringComparison.Ordinal)),
            "firewall verify next action must show non-mutating verification and product rule profile");
    }
    

    public static void FirewallRowsExposeProductVerification()
    {
        var listener = JsonSerializer.SerializeToElement(new
        {
            product_rule_verified = true,
            expected_rule_name = "Rusty Hostess WPF QCL-080 UDP Freshness 18767",
            expected_remote_address = "LocalSubnet",
        });
        var report = new ConnectivityFirewallRuleReport
        {
            Status = "pass",
            Action = "verify",
            Rule = new ConnectivityFirewallRule
            {
                Name = "Rusty Hostess WPF QCL-080 UDP Freshness 18767",
                Program = "C:\\Program Files\\Rusty Hostess\\HostessCompanion.Wpf.exe",
                Protocol = "UDP",
                LocalPort = 18767,
                Profiles = ["Public"],
                RemoteAddress = "LocalSubnet",
                ScopeNote = "product scoped listener",
            },
            Verification = new ConnectivityFirewallVerification
            {
                Status = "pass",
                ProductRuleVerified = true,
                AllowedOnActiveProfile = true,
                ListenerFirewall = listener,
            },
        };
    
        var rows = ConnectivityRows.ForFirewallPlan(report);
    
        Assert(rows.Any(row => row.Name == "host.windows_firewall_rule_verify" && row.Status == "pass"),
            "missing verify action row");
        Assert(rows.Any(row => row.Evidence.Contains("product_rule_verified=True", StringComparison.Ordinal)),
            "missing product verification evidence");
        Assert(ConnectivityRows.StatusFromRows(rows) == "pass", "verified product rule should pass");
    }
    

    public static void FirewallRowsExposeElevationPreflight()
    {
        var report = new ConnectivityFirewallRuleReport
        {
            Status = "blocked",
            Action = "apply",
            Rule = new ConnectivityFirewallRule
            {
                Name = "Rusty Hostess WPF QCL-082 TCP RMANVID1 Media 9079",
                Program = "C:\\Program Files\\Rusty Hostess\\HostessCompanion.Wpf.exe",
                Protocol = "TCP",
                LocalPort = 9079,
                Profiles = ["Public"],
                RemoteAddress = "LocalSubnet",
                ScopeNote = "product scoped listener",
            },
            Elevation = new ConnectivityFirewallElevation
            {
                RequiresAdmin = true,
                CurrentProcessIsElevated = false,
                MutationPermitted = false,
                BlockedBeforeMutation = true,
                Handoff = new ConnectivityFirewallElevationHandoff
                {
                    OperatorAction = "rerun from elevated PowerShell",
                    ScriptOut = "target\\connectivity-probe\\wpf-firewall-rule-apply.admin-handoff.ps1",
                    ScriptSha256 = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
                    HostessActionCommand = "python tools/hostessctl/hostessctl.py connectivity-probe windows-firewall-rule --action apply",
                    HostessVerifyCommand = "python tools/hostessctl/hostessctl.py connectivity-probe windows-firewall-rule --action verify",
                    VerifyReportOut = "target\\connectivity-probe\\wpf-firewall-rule-apply.verify.json",
                },
            },
            AdminHandoff = new ConnectivityFirewallAdminHandoff
            {
                HandoffKind = "hostess_cli_elevated_firewall_lifecycle",
                HandoffAction = "apply",
                ScriptOut = "target\\connectivity-probe\\wpf-firewall-rule-apply.admin-handoff.ps1",
                VerifyReportOut = "target\\connectivity-probe\\wpf-firewall-rule-apply.verify.json",
                ScriptSha256 = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
                HostessActionCommand = "python tools/hostessctl/hostessctl.py connectivity-probe windows-firewall-rule --action apply",
                HostessVerifyCommand = "python tools/hostessctl/hostessctl.py connectivity-probe windows-firewall-rule --action verify",
                OperatorNote = "Run the generated script from an elevated PowerShell session.",
            },
            ActionResult = new ConnectivityProcessResult
            {
                Attempted = false,
                Stderr = "firewall apply requires an elevated PowerShell session",
            },
        };
    
        var rows = ConnectivityRows.ForFirewallPlan(report);
        var elevation = rows.Single(row => row.Name == "host.windows_firewall_rule_elevation");
    
        Assert(elevation.Status == "blocked", "non-elevated firewall mutation must project blocked");
        Assert(elevation.IssueCodes.Contains("hostess.issue.connectivity_probe.firewall_rule_requires_elevation"),
            "missing elevation issue code");
        Assert(elevation.Evidence.Contains("handoff_script=target\\connectivity-probe\\wpf-firewall-rule-apply.admin-handoff.ps1", StringComparison.Ordinal),
            "blocked preflight must expose the generated admin handoff script");
        Assert(elevation.Evidence.Contains("verify_report=target\\connectivity-probe\\wpf-firewall-rule-apply.verify.json", StringComparison.Ordinal),
            "blocked preflight must expose the post-admin verify report");
        Assert(elevation.Notes.Contains("hostess_action=python tools/hostessctl/hostessctl.py", StringComparison.Ordinal),
            "blocked preflight must expose the Hostess CLI action command");
        Assert(rows.All(row => row.Name != "host.windows_firewall_rule_apply_process"),
            "blocked preflight must not project an attempted mutation process row");
    }
    

    public static void FirewallServiceUsesCliAdminHandoff()
    {
        var repoRoot = LocateHostessRepoRoot();
        var servicePath = Path.Combine(
            repoRoot.FullName,
            "apps",
            "hostess-companion-wpf",
            "Services",
            "HostessctlConnectivityService.cs");
        var source = File.ReadAllText(servicePath);
    
        Assert(!source.Contains("Verb = \"runas\"", StringComparison.Ordinal),
            "WPF service must not own a hidden elevated firewall launcher");
        Assert(!source.Contains("RunElevatedHostessctlAsync", StringComparison.Ordinal),
            "WPF service must use Hostess CLI handoff instead of a private elevated runner");
        Assert(source.Contains("--handoff-script-out", StringComparison.Ordinal),
            "WPF apply/remove must request a Hostess-generated admin handoff script");
        Assert(source.Contains("--handoff-verify-out", StringComparison.Ordinal),
            "WPF apply/remove must request the matching Hostess verification report");
    }
    

    public static void FirewallDefaultNamesStayProductScoped()
    {
        var vm = new MainWindowViewModel(
            new HostessctlReadinessService(),
            new HostessctlCatalogService(),
            new HostessctlCommandService(),
            new HostessctlSessionService(),
            new HostessctlConnectivityService());
    
        Assert(vm.ConnectivityRuleName == "Rusty Hostess WPF QCL-080 UDP Freshness 18767",
            "initial UDP firewall rule name must be WPF product scoped");
        Assert(vm.ConnectivityRuleProfile == HostessctlConnectivityService.FirewallRuleProfileQcl080UdpFreshness,
            "initial firewall rule profile must be the QCL-080 product UDP profile");
        Assert(vm.ConnectivityRuleProfiles.Contains(HostessctlConnectivityService.FirewallRuleProfileQcl082Rmanvid1Media),
            "WPF must expose the QCL-082 product media listener firewall profile");
    
        vm.ConnectivityPort = "19000";
        Assert(vm.ConnectivityRuleName == "Rusty Hostess WPF QCL-080 UDP Freshness 19000",
            "UDP port changes must preserve WPF product-scoped rule name");
    
        vm.ConnectivityProtocol = "TCP";
        Assert(vm.ConnectivityRuleName == "Rusty Hostess WPF QCL-010 TCP Echo 19000",
            "protocol changes must preserve WPF product-scoped rule name");
    
        vm.ConnectivityPort = "18766";
        Assert(vm.ConnectivityRuleName == "Rusty Hostess WPF QCL-010 TCP Echo 18766",
            "TCP port changes must preserve WPF product-scoped rule name");
        Assert(vm.ConnectivityRuleProfile == HostessctlConnectivityService.FirewallRuleProfileQcl010TcpEcho,
            "TCP manual selection must switch to the QCL-010 product TCP profile");
    
        vm.ConnectivityRuleProfile = HostessctlConnectivityService.FirewallRuleProfileQcl082Rmanvid1Media;
        Assert(vm.ConnectivityProtocol == "TCP", "QCL-082 product profile must select TCP");
        Assert(vm.ConnectivityPort == "9079", "QCL-082 product profile must select the RMANVID1 media listener port");
        Assert(vm.ConnectivityRuleName == "Rusty Hostess WPF QCL-082 TCP RMANVID1 Media 9079",
            "QCL-082 product profile must project the product media listener rule name");
    
        vm.ConnectivityRuleName = "Rusty Hostess WPF Manual Override";
        Assert(vm.ConnectivityRuleProfile == HostessctlConnectivityService.FirewallRuleProfileCustom,
            "manual rule-name edits must switch WPF back to the custom CLI profile");
    }
    

    public static void FirewallQcl082ProfilePlanUsesCliProfile()
    {
        var service = new HostessctlConnectivityService();
        var report = service.PlanFirewallRuleAsync(
                "C:\\Program Files\\Rusty Hostess\\HostessCompanion.Wpf.exe",
                "",
                "",
                "Public",
                "LocalSubnet",
                "",
                HostessctlConnectivityService.FirewallRuleProfileQcl082Rmanvid1Media,
                CancellationToken.None)
            .GetAwaiter()
            .GetResult();
    
        Assert(report.RuleProfile == HostessctlConnectivityService.FirewallRuleProfileQcl082Rmanvid1Media,
            "WPF plan route must emit the QCL-082 CLI rule profile");
        Assert(report.ProbeUsage.ProbeId == "QCL-082", "QCL-082 firewall profile must bind the media listener probe id");
        Assert(report.ProbeUsage.ConnectivityProbeArgs.Contains("--media-stream-firewall-report"),
            "QCL-082 firewall profile must advertise the media-stream firewall report probe argument");
        Assert(report.Rule.Protocol == "TCP", "QCL-082 firewall profile must use TCP");
        Assert(report.Rule.LocalPort == 9079, "QCL-082 firewall profile must use the RMANVID1 media listener port");
        Assert(report.Rule.Name == "Rusty Hostess WPF QCL-082 TCP RMANVID1 Media 9079",
            "QCL-082 firewall profile must use the product-owned listener rule name");
    }
    

}
