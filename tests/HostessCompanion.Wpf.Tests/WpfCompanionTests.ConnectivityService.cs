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
    public static void ConnectivityServiceBuildsCompanionReportProjectionArtifact()
    {
        var repoRoot = LocateHostessRepoRoot();
        var isolatedLatestArtifactDir = Path.Combine(
            repoRoot.FullName,
            "target",
            "connectivity-probe",
            $"wpf-fixture-latest-{Guid.NewGuid():N}");
        Directory.CreateDirectory(isolatedLatestArtifactDir);
        var previousLatestArtifactDir = Environment.GetEnvironmentVariable(
            HostessctlConnectivityService.LatestArtifactDirEnvironmentVariable);
        ConnectivityProtocolMatrixProjectionRun run;
        try
        {
            Environment.SetEnvironmentVariable(
                HostessctlConnectivityService.LatestArtifactDirEnvironmentVariable,
                isolatedLatestArtifactDir);
    
            run = new HostessctlConnectivityService()
                .RunProtocolMatrixProjectionAsync(
                    serial: "",
                    program: "",
                    protocol: "UDP",
                    portText: "18767",
                    cancellationToken: CancellationToken.None)
                .GetAwaiter()
                .GetResult();
        }
        finally
        {
            Environment.SetEnvironmentVariable(
                HostessctlConnectivityService.LatestArtifactDirEnvironmentVariable,
                previousLatestArtifactDir);
            if (Directory.Exists(isolatedLatestArtifactDir))
            {
                Directory.Delete(isolatedLatestArtifactDir, recursive: true);
            }
        }
    
        Assert(run.Suite.ReportPath.EndsWith(".json", StringComparison.Ordinal),
            "suite report path must be attached");
        Assert(run.Matrix.ReportPath.EndsWith(".protocol-matrix.json", StringComparison.Ordinal),
            "matrix report path must be attached");
        Assert(File.Exists(run.DirectWifiProductMediaPlanPath),
            "direct-Wi-Fi product-media acceptance plan must be written");
        Assert(run.DirectWifiProductMediaPlanPath.EndsWith(".direct-wifi-product-media-acceptance-plan.json", StringComparison.Ordinal),
            "direct-Wi-Fi product-media acceptance plan path must be run-scoped");
        Assert(File.Exists(run.Projection.ReportPath), "projection report must be written");
        Assert(File.Exists(run.TransportGates.ReportPath), "transport gate report must be written");
        Assert(File.Exists(run.TransportGates.ValidationReportPath),
            "transport gate validation sidecar must be written");
        Assert(run.TransportGates.ValidationReportPath.EndsWith(".transport-gates.validation-report.json", StringComparison.Ordinal),
            "transport gate validation sidecar path must be run-scoped");
        Assert(run.TransportGates.ValidationReport is not null,
            "transport gate validation sidecar must be loaded for WPF inspection");
        Assert(run.TransportGates.ValidationReport!.Schema == "rusty.hostess.companion.transport_gate_report.validation.v1",
            "transport gate validation sidecar schema must be preserved");
        Assert(run.TransportGates.ValidationReport.ReportId == run.TransportGates.ReportId,
            "transport gate validation sidecar must identify the loaded transport-gate report");
        Assert(run.TransportGates.ValidationReport.SourceProjection == run.Projection.ReportPath,
            "transport gate validation sidecar must identify the loaded projection artifact");
        Assert(run.TransportGates.ValidationReport.Issues.Any(issue =>
                issue.IssueCode == "hostess.issue.transport_gates.gate_pending"),
            "transport gate validation sidecar must preserve structured issue codes");
        Assert(run.Projection.Schema == "rusty.hostess.companion.report_projection.v1",
            "service must return the companion-report projection schema");
        Assert(run.TransportGates.Schema == "rusty.hostess.companion.transport_gate_report.v1",
            "service must return the companion transport-gate report schema");
        Assert(run.Projection.Rows.Any(row => row.RowId == "protocol_matrix.summary"),
            "projection must include the protocol matrix summary row");
        Assert(run.TransportGates.Authority.ProjectionOnly,
            "transport gate report must remain projection-only authority");
        Assert(run.TransportGates.SourceProjection.Path == run.Projection.ReportPath,
            "transport gate report must derive from the WPF companion projection artifact");
        Assert(run.Projection.SourceArtifacts.Any(source => source.Role == "connectivity_suite_run"),
            "projection must include the suite source artifact");
        Assert(run.Projection.SourceArtifacts.Any(source => source.Role == "connectivity_probe_report"),
            "projection must include protocol-matrix source probe artifacts");
        var topologyArtifacts = new[]
        {
            ("QCL-020", $"{run.Suite.SuiteRunId}.qcl020-wifi-adb-session-pass.json"),
            ("QCL-030", $"{run.Suite.SuiteRunId}.qcl030-local-only-hotspot-started.json"),
            ("QCL-040", $"{run.Suite.SuiteRunId}.qcl040-wifi-direct-phone-peer-pass.json"),
            ("QCL-041", $"{run.Suite.SuiteRunId}.qcl041-wifi-direct-windows-peer-pass.json"),
        };
        foreach (var (probeId, artifactName) in topologyArtifacts)
        {
            Assert(run.Matrix.Inputs.Any(input =>
                    input.Role == "connectivity_probe_report"
                    && input.Path.EndsWith(artifactName, StringComparison.Ordinal)),
                $"protocol matrix must consume generated topology fixture report {probeId}");
            Assert(run.Projection.SourceArtifacts.Any(source =>
                    source.Role == "connectivity_probe_report"
                    && source.Path.EndsWith(artifactName, StringComparison.Ordinal)),
                $"projection must include generated topology fixture report {probeId}");
            Assert(run.Projection.Rows.Any(row => row.RowId == $"connectivity_probe.topology.{probeId}"),
                $"projection must include topology row {probeId}");
            Assert(run.Projection.Rows.Any(row => row.RowId == $"connectivity_probe.transport.{probeId}"),
                $"projection must include transport row {probeId}");
        }
        var firewallArtifact = $"{run.Suite.SuiteRunId}.qcl082-product-firewall-verify.json";
        Assert(run.Projection.SourceArtifacts.Any(source =>
                source.Role == "firewall_rule_report"
                && source.Path.EndsWith(firewallArtifact, StringComparison.Ordinal)),
            "projection must include the read-only QCL-082 product firewall verify report");
        Assert(run.Projection.SourceArtifacts.Any(source =>
                source.Role == "direct_wifi_product_media_acceptance_plan"
                && source.Path == run.DirectWifiProductMediaPlanPath),
            "projection must include the generated direct-Wi-Fi product-media acceptance plan");
        var firewallRow = run.Projection.Rows.Single(row =>
            row.RowId == "firewall_rule.qcl-082-rmanvid1-media.verify");
        Assert(firewallRow.AuthorityOwner == "tools.hostessctl.connectivity_firewall",
            "QCL-082 firewall projection row must keep Hostess firewall ownership");
        Assert(firewallRow.Details.GetProperty("product_gate").GetString()
            == "product_tcp_media_listener_firewall_verified",
            "QCL-082 firewall projection row must name only the listener firewall product gate");
        var firewallGateProven = firewallRow.Details.TryGetProperty("product_gate_proven", out var gateProven)
            && gateProven.ValueKind == JsonValueKind.True;
        var coverage = run.Projection.Rows.Single(row => row.RowId == "transport_coverage.summary");
        var directWifiPlanRow = run.Projection.Rows.Single(row =>
            row.RowId == "direct_wifi_product_media_plan.summary");
        Assert(directWifiPlanRow.AuthorityOwner == "tools.hostessctl.connectivity_direct_wifi_product_media_plan",
            "direct-Wi-Fi product-media plan row must keep Hostess CLI plan ownership");
        Assert(directWifiPlanRow.Status == "planned",
            "fixture-only WPF run must not promote the direct-Wi-Fi product-media plan");
        Assert(directWifiPlanRow.Details.GetProperty("policy").GetProperty("read_only_plan").GetBoolean(),
            "direct-Wi-Fi product-media plan must be a read-only artifact");
        Assert(directWifiPlanRow.Details.GetProperty("readiness").GetProperty("live_steps_require_quest_lease").GetBoolean(),
            "direct-Wi-Fi product-media plan must preserve Quest lease requirements for live steps");
        var directWifiDependencyRow = run.Projection.Rows.Single(row =>
            row.RowId == "direct_wifi_product_media_plan.dependency.transport.direct_wifi_live_topology");
        Assert(directWifiDependencyRow.Status == "planned",
            "generated acceptance plan must keep unpromoted direct-Wi-Fi topology planned");
        Assert(directWifiDependencyRow.Details.GetProperty("network_provider").GetString() == "wifi_direct",
            "direct-Wi-Fi acceptance dependency must keep Wi-Fi Direct visible to the projection");
        var productMediaDependencyRow = run.Projection.Rows.Single(row =>
            row.RowId == "direct_wifi_product_media_plan.dependency.transport.product_tcp_media_over_direct_wifi");
        Assert(productMediaDependencyRow.Status == "planned",
            "generated acceptance plan must keep product TCP media over direct Wi-Fi planned");
        Assert(productMediaDependencyRow.Details.GetProperty("network_provider").GetString() == "wifi_direct",
            "product media dependency must preserve the direct-Wi-Fi topology requirement");
        Assert(productMediaDependencyRow.Details.GetProperty("route").GetString() == "rmanvid1_receiver_capture",
            "product media dependency must preserve the receiver-capture route");
        var directWifiPlanRows = ConnectivityRows.ForCompanionReportProjection(run.Projection);
        Assert(directWifiPlanRows.Any(row =>
                row.Name == "direct_wifi_product_media_plan.summary"
                && row.Evidence.Contains("topology=", StringComparison.Ordinal)),
            "WPF row projection must render the generated direct-Wi-Fi product-media acceptance plan");
        Assert(directWifiPlanRows.Any(row =>
                row.Name == "direct_wifi_product_media_plan.dependency.transport.product_tcp_media_over_direct_wifi"
                && row.Observed.GetProperty("Details").GetProperty("network_provider").GetString() == "wifi_direct"
                && row.Observed.GetProperty("Details").GetProperty("route").GetString() == "rmanvid1_receiver_capture"),
            "WPF row projection must preserve the product-media direct-Wi-Fi dependency details");
        Assert(directWifiPlanRows.Any(row =>
                row.Name == "direct_wifi_product_media_plan.command.qcl082_run_qcl082_product_media_live_session"
                && row.Evidence.Contains("qcl082-product-media-live-session", StringComparison.Ordinal)
                && row.Notes.Contains("requires_quest_lease=True", StringComparison.Ordinal)
                && row.Notes.Contains("depends_on=transport.direct_wifi_live_topology,transport.product_tcp_media_listener_firewall", StringComparison.Ordinal)
                && row.Notes.Contains("media-stream-receiver-result.json", StringComparison.Ordinal)),
            "WPF row projection must render the direct-Wi-Fi product-media live-session command row");
        Assert(coverage.Evidence.Contains("websocket", StringComparison.Ordinal),
            "projection coverage must keep WebSocket command route visible");
        Assert(coverage.Evidence.Contains("tcp", StringComparison.Ordinal),
            "projection coverage must keep TCP transport visible");
        Assert(coverage.Evidence.Contains("wifi_direct", StringComparison.Ordinal),
            "projection coverage must keep Wi-Fi Direct topology visible");
        var explicitTerms = coverage.Details.GetProperty("explicit_terms");
        Assert(explicitTerms.GetProperty("websocket").GetBoolean(),
            "projection coverage must mark WebSocket as explicit");
        Assert(explicitTerms.GetProperty("tcp").GetBoolean(),
            "projection coverage must mark TCP as explicit");
        Assert(explicitTerms.GetProperty("wifi_direct").GetBoolean(),
            "projection coverage must mark Wi-Fi Direct as explicit");
        var generatedTermGates = coverage.Details.GetProperty("term_gates");
        Assert(generatedTermGates.GetProperty("websocket").GetProperty("scope").GetString() == "manifold_command_session_receipts_and_qcl079_generic_protocol_fit",
            "generated coverage must scope WebSocket as command receipts plus QCL-079 generic protocol fit");
        Assert(generatedTermGates.GetProperty("tcp").GetProperty("scope").GetString() == "qcl010_qcl011_echo_and_qcl082_tcp_binary_media",
            "generated coverage must scope TCP as topology echo and QCL-082 media");
        Assert(generatedTermGates.GetProperty("wifi_direct").GetProperty("scope").GetString() == "qcl040_qcl041_topology_evidence",
            "generated coverage must scope Wi-Fi Direct as topology evidence");
        var remainingGateIds = coverage.Details.GetProperty("remaining_live_gates")
            .EnumerateArray()
            .Select(gate => gate.GetProperty("gate_id").GetString())
            .ToHashSet(StringComparer.Ordinal);
        if (ManifoldWebSocketStreamEvidenceExists())
        {
            var qcl079Artifact = $"{run.Suite.SuiteRunId}.qcl079-manifold-websocket-stream.json";
            Assert(run.Matrix.Inputs.Any(input =>
                    input.Role == "connectivity_probe_report"
                    && input.Path.EndsWith(qcl079Artifact, StringComparison.Ordinal)),
                "protocol matrix must consume the QCL-079 Manifold WebSocket stream evidence artifact");
            Assert(run.Projection.SourceArtifacts.Any(source =>
                    source.Role == "connectivity_probe_report"
                    && source.Path.EndsWith(qcl079Artifact, StringComparison.Ordinal)),
                "projection must include the QCL-079 Manifold WebSocket stream evidence artifact");
            Assert(!remainingGateIds.Contains("transport.general_websocket_capability"),
                "generated coverage must clear generic WebSocket once QCL-079 has broker-owned evidence");
        }
        else
        {
            Assert(remainingGateIds.Contains("transport.general_websocket_capability"),
                "generated coverage must state generic WebSocket still needs promoted broker or Quest runtime evidence");
        }
        Assert(remainingGateIds.Contains("transport.direct_wifi_live_topology"),
            "generated coverage must state direct Wi-Fi still needs live topology evidence");
        Assert(remainingGateIds.Contains("transport.product_tcp_media_over_direct_wifi"),
            "generated coverage must state product TCP media over direct Wi-Fi still needs live evidence");
        if (firewallGateProven)
        {
            Assert(!remainingGateIds.Contains("transport.product_tcp_media_listener_firewall"),
                "verified product firewall report must clear only the listener firewall gate");
        }
        else
        {
            Assert(remainingGateIds.Contains("transport.product_tcp_media_listener_firewall"),
                "unverified product firewall report must leave listener firewall evidence pending");
        }
        var transportGateRows = ConnectivityRows.ForTransportGateReport(run.TransportGates);
        Assert(transportGateRows.Any(row =>
                row.Name == "hostess.companion_transport_gates"
                && row.Notes.Contains($"validation_report={run.TransportGates.ValidationReportPath}", StringComparison.Ordinal)),
            "transport gate summary row must expose the validation sidecar path");
        Assert(transportGateRows.Any(row =>
                row.Name == "transport.direct_wifi_live_topology.run_qcl040_live_wifi_direct_preflight"
                && row.Notes.Contains("requires_quest_lease=True", StringComparison.Ordinal)),
            "transport gate rows must project direct-Wi-Fi Quest lease requirements");
        Assert(transportGateRows.Any(row =>
                row.Name == "transport.direct_wifi_live_topology.plan_qcl041_wifi_direct_lifecycle"
                && row.Notes.Contains("requires_quest_lease=False", StringComparison.Ordinal)
                && row.Notes.Contains("authority_owner=tools.hostessctl.connectivity_topology_lifecycle_plan", StringComparison.Ordinal)
                && row.Evidence.Contains("wifi-direct-lifecycle-plan", StringComparison.Ordinal)
                && row.Evidence.Contains("--serial '<quest-serial>'", StringComparison.Ordinal)),
            "transport gate rows must project the non-mutating Wi-Fi Direct lifecycle plan route");
        if (remainingGateIds.Contains("transport.product_tcp_media_listener_firewall"))
        {
            Assert(transportGateRows.Any(row =>
                    row.Name == "transport.product_tcp_media_listener_firewall.run_qcl082_firewall_admin_handoff"
                    && row.Notes.Contains("requires_elevation=True", StringComparison.Ordinal)),
                "transport gate rows must project QCL-082 firewall elevation requirements");
            Assert(transportGateRows.Any(row =>
                    row.Name == "transport.product_tcp_media_listener_firewall.verify_qcl082_product_firewall_rule"
                    && row.Evidence.Contains("--rule-profile qcl-082-rmanvid1-media", StringComparison.Ordinal)),
                "transport gate rows must project the product firewall verify CLI route");
        }
        if (RustyQuestMediaStreamSessionPlanExists())
        {
            var sourceContractArtifact = $"{run.Suite.SuiteRunId}.qcl082-media-stream-session-plan.json";
            Assert(run.Matrix.Inputs.Any(input =>
                    input.Role == "connectivity_probe_report"
                    && input.Path.EndsWith(sourceContractArtifact, StringComparison.Ordinal)),
                "protocol matrix must consume the QCL-082 Rusty Quest media-stream source-contract artifact");
            Assert(run.Projection.SourceArtifacts.Any(source =>
                    source.Role == "connectivity_probe_report"
                    && source.Path.EndsWith(sourceContractArtifact, StringComparison.Ordinal)),
                "projection must include the QCL-082 Rusty Quest media-stream source-contract artifact");
        }
    }
    

    public static void ConnectivityServiceForwardsPromotedDirectWifiTopologyInput()
    {
        var repoRoot = LocateHostessRepoRoot();
        var stamp = DateTimeOffset.UtcNow.ToString("yyyyMMdd-HHmmss-fff", CultureInfo.InvariantCulture);
        var suiteRunId = $"wpf-promoted-direct-wifi-topology-{stamp}";
        var artifactDir = Path.Combine(repoRoot.FullName, "target", "connectivity-probe");
        var reportDir = Path.Combine(repoRoot.FullName, "target", "companion-report");
        Directory.CreateDirectory(artifactDir);
        Directory.CreateDirectory(reportDir);
    
        var promotedTopologyPath = Path.Combine(artifactDir, $"{suiteRunId}.qcl041-promoted-wifi-direct-lifecycle.json");
        var candidateTopologyPath = Path.Combine(artifactDir, $"{suiteRunId}.qcl041-candidate-wifi-direct-fixture.json");
        FileInfo? planPath = null;
        try
        {
            DirectWifiProductMediaPlanTestArtifacts.WriteDirectWifiTopologyReport(
                promotedTopologyPath,
                "QCL-041",
                promoted: true);
            DirectWifiProductMediaPlanTestArtifacts.WriteDirectWifiTopologyReport(
                candidateTopologyPath,
                "QCL-041",
                promoted: false);
    
            var matrix = new ConnectivityProtocolEvidenceMatrix
            {
                MatrixId = $"{suiteRunId}.matrix",
                ReportPath = Path.Combine(artifactDir, $"{suiteRunId}.protocol-matrix.json"),
                Inputs =
                [
                    new ConnectivityProtocolEvidenceInput
                    {
                        Role = "connectivity_probe_report",
                        Path = Path.GetRelativePath(repoRoot.FullName, promotedTopologyPath),
                        Schema = "rusty.quest.connectivity_topology_probe.v1",
                        Status = "pass",
                    },
                    new ConnectivityProtocolEvidenceInput
                    {
                        Role = "connectivity_probe_report",
                        Path = candidateTopologyPath,
                        Schema = "rusty.quest.connectivity_topology_probe.v1",
                        Status = "pass",
                    },
                ],
            };
            var suite = new ConnectivitySuiteRunReport
            {
                SuiteRunId = suiteRunId,
                ReportPath = Path.Combine(artifactDir, $"{suiteRunId}.suite.json"),
            };
            var method = typeof(HostessctlConnectivityService).GetMethod(
                    "RunDirectWifiProductMediaPlanAsync",
                    BindingFlags.NonPublic | BindingFlags.Static)
                ?? throw new InvalidOperationException("missing RunDirectWifiProductMediaPlanAsync method");
            var task = (Task<FileInfo>)method.Invoke(
                    null,
                    new object?[]
                    {
                        repoRoot,
                        suite,
                        matrix,
                        new List<FileInfo> { new(candidateTopologyPath) },
                        null,
                        new FileInfo(Path.Combine(reportDir, $"{suiteRunId}.projection.json")),
                        new FileInfo(Path.Combine(reportDir, $"{suiteRunId}.transport-gates.json")),
                        "C:\\Program Files\\Rusty Hostess\\HostessCompanion.Wpf.exe",
                        CancellationToken.None,
                    })!
                ?? throw new InvalidOperationException("direct-Wi-Fi product-media plan task was empty");
            planPath = task.GetAwaiter().GetResult();
    
            using var document = JsonDocument.Parse(File.ReadAllText(planPath.FullName));
            var root = document.RootElement;
            var artifacts = root.GetProperty("artifacts");
            Assert(artifacts.GetProperty("promoted_topology_report").GetString() == promotedTopologyPath,
                "WPF acceptance-plan route must forward the promoted topology report path");
            var readiness = root.GetProperty("readiness");
            Assert(readiness.GetProperty("direct_wifi_topology_ready").GetBoolean(),
                "promoted topology input must satisfy only the topology readiness dependency");
            Assert(!readiness.GetProperty("product_tcp_media_over_direct_wifi_ready").GetBoolean(),
                "promoted topology alone must not clear the QCL-082 product media gate");
            var topologyDependency = root.GetProperty("dependencies")
                .EnumerateArray()
                .Single(dependency => dependency.GetProperty("gate_id").GetString() == "transport.direct_wifi_live_topology");
            var selected = topologyDependency.GetProperty("selected");
            Assert(selected.GetProperty("selected_candidate_id").GetString() == "explicit_promoted_topology",
                "Hostess plan must select the explicit promoted topology candidate");
            Assert(selected.GetProperty("report_path").GetString() == promotedTopologyPath,
                "Hostess plan must not select the non-promoted topology fixture");
        }
        finally
        {
            foreach (var path in new[]
            {
                promotedTopologyPath,
                candidateTopologyPath,
                planPath?.FullName,
            })
            {
                if (!string.IsNullOrWhiteSpace(path) && File.Exists(path))
                {
                    File.Delete(path);
                }
            }
        }
    }
    

    public static void ConnectivityServiceForwardsQcl082ProductMediaInput()
    {
        var repoRoot = LocateHostessRepoRoot();
        var stamp = DateTimeOffset.UtcNow.ToString("yyyyMMdd-HHmmss-fff", CultureInfo.InvariantCulture);
        var suiteRunId = $"wpf-qcl082-product-media-forwarding-{stamp}";
        var artifactDir = Path.Combine(repoRoot.FullName, "target", "connectivity-probe");
        var reportDir = Path.Combine(repoRoot.FullName, "target", "companion-report");
        Directory.CreateDirectory(artifactDir);
        Directory.CreateDirectory(reportDir);
    
        var promotedTopologyPath = Path.Combine(artifactDir, $"{suiteRunId}.qcl041-promoted-wifi-direct-lifecycle.json");
        var candidateProductMediaPath = Path.Combine(artifactDir, $"{suiteRunId}.qcl082-candidate-product-media.json");
        var promotedProductMediaPath = Path.Combine(artifactDir, $"{suiteRunId}.qcl082-promoted-product-media.json");
        FileInfo? planPath = null;
        try
        {
            DirectWifiProductMediaPlanTestArtifacts.WriteDirectWifiTopologyReport(
                promotedTopologyPath,
                "QCL-041",
                promoted: true);
            DirectWifiProductMediaPlanTestArtifacts.WriteQcl082ProductMediaReport(
                candidateProductMediaPath,
                promoted: false);
            DirectWifiProductMediaPlanTestArtifacts.WriteQcl082ProductMediaReport(
                promotedProductMediaPath,
                promoted: true);
    
            var matrix = new ConnectivityProtocolEvidenceMatrix
            {
                MatrixId = $"{suiteRunId}.matrix",
                ReportPath = Path.Combine(artifactDir, $"{suiteRunId}.protocol-matrix.json"),
                Inputs =
                [
                    new ConnectivityProtocolEvidenceInput
                    {
                        Role = "connectivity_probe_report",
                        Path = candidateProductMediaPath,
                        Schema = "rusty.quest.connectivity_probe.v1",
                        Status = "pass",
                    },
                    new ConnectivityProtocolEvidenceInput
                    {
                        Role = "connectivity_probe_report",
                        Path = Path.GetRelativePath(repoRoot.FullName, promotedTopologyPath),
                        Schema = "rusty.quest.connectivity_topology_probe.v1",
                        Status = "pass",
                    },
                    new ConnectivityProtocolEvidenceInput
                    {
                        Role = "connectivity_probe_report",
                        Path = promotedProductMediaPath,
                        Schema = "rusty.quest.connectivity_probe.v1",
                        Status = "pass",
                    },
                ],
            };
            var suite = new ConnectivitySuiteRunReport
            {
                SuiteRunId = suiteRunId,
                ReportPath = Path.Combine(artifactDir, $"{suiteRunId}.suite.json"),
            };
            var method = typeof(HostessctlConnectivityService).GetMethod(
                    "RunDirectWifiProductMediaPlanAsync",
                    BindingFlags.NonPublic | BindingFlags.Static)
                ?? throw new InvalidOperationException("missing RunDirectWifiProductMediaPlanAsync method");
            var task = (Task<FileInfo>)method.Invoke(
                    null,
                    new object?[]
                    {
                        repoRoot,
                        suite,
                        matrix,
                        new List<FileInfo>(),
                        null,
                        new FileInfo(Path.Combine(reportDir, $"{suiteRunId}.projection.json")),
                        new FileInfo(Path.Combine(reportDir, $"{suiteRunId}.transport-gates.json")),
                        "C:\\Program Files\\Rusty Hostess\\HostessCompanion.Wpf.exe",
                        CancellationToken.None,
                    })!
                ?? throw new InvalidOperationException("direct-Wi-Fi product-media plan task was empty");
            planPath = task.GetAwaiter().GetResult();
    
            using var document = JsonDocument.Parse(File.ReadAllText(planPath.FullName));
            var root = document.RootElement;
            var artifacts = root.GetProperty("artifacts");
            Assert(artifacts.GetProperty("promoted_topology_report").GetString() == promotedTopologyPath,
                "WPF acceptance-plan route must still forward promoted direct-Wi-Fi topology");
            Assert(artifacts.GetProperty("qcl082_report").GetString() == promotedProductMediaPath,
                "WPF acceptance-plan route must forward the promoted QCL-082 product-media report path");
            var readiness = root.GetProperty("readiness");
            Assert(readiness.GetProperty("direct_wifi_topology_ready").GetBoolean(),
                "promoted topology input must satisfy topology readiness");
            Assert(readiness.GetProperty("product_tcp_media_over_direct_wifi_ready").GetBoolean(),
                "promoted product-media input must satisfy QCL-082 product media readiness");
            Assert(readiness.GetProperty("all_remaining_transport_gates_ready").GetBoolean(),
                "topology plus product media evidence must satisfy remaining product transport readiness");
            var productMediaDependency = root.GetProperty("dependencies")
                .EnumerateArray()
                .Single(dependency =>
                    dependency.GetProperty("gate_id").GetString() == "transport.product_tcp_media_over_direct_wifi");
            Assert(productMediaDependency.GetProperty("summary").GetProperty("report_path").GetString()
                == promotedProductMediaPath,
                "Hostess plan must not select the non-promoting QCL-082 candidate report");
        }
        finally
        {
            foreach (var path in new[]
            {
                promotedTopologyPath,
                candidateProductMediaPath,
                promotedProductMediaPath,
                planPath?.FullName,
            })
            {
                if (!string.IsNullOrWhiteSpace(path) && File.Exists(path))
                {
                    File.Delete(path);
                }
            }
        }
    }
    

    public static void ConnectivityServiceFindsSiblingQcl082ProductMediaArtifact()
    {
        var repoRoot = LocateHostessRepoRoot();
        var stamp = DateTimeOffset.UtcNow.ToString("yyyyMMdd-HHmmss-fff", CultureInfo.InvariantCulture);
        var suiteRunId = $"wpf-qcl082-product-media-sibling-{stamp}";
        var artifactDir = Path.Combine(repoRoot.FullName, "target", "connectivity-probe");
        var reportDir = Path.Combine(repoRoot.FullName, "target", "companion-report");
        var questLifecycleDir = Path.GetFullPath(Path.Combine(
            repoRoot.FullName,
            "..",
            "rusty-quest",
            "target",
            "qcl041-wifi-direct-lifecycle",
            suiteRunId));
        Directory.CreateDirectory(artifactDir);
        Directory.CreateDirectory(reportDir);
        Directory.CreateDirectory(questLifecycleDir);
    
        var promotedTopologyPath = Path.Combine(artifactDir, $"{suiteRunId}.qcl041-promoted-wifi-direct-lifecycle.json");
        var siblingProductMediaPath = Path.Combine(questLifecycleDir, "qcl082-product-media-live-qcl082.json");
        var previousLatestArtifactDir = Environment.GetEnvironmentVariable(
            HostessctlConnectivityService.LatestArtifactDirEnvironmentVariable);
        FileInfo? planPath = null;
        try
        {
            Environment.SetEnvironmentVariable(
                HostessctlConnectivityService.LatestArtifactDirEnvironmentVariable,
                questLifecycleDir);
            DirectWifiProductMediaPlanTestArtifacts.WriteDirectWifiTopologyReport(
                promotedTopologyPath,
                "QCL-041",
                promoted: true);
            DirectWifiProductMediaPlanTestArtifacts.WriteQcl082ProductMediaReport(
                siblingProductMediaPath,
                promoted: true);
    
            var matrix = new ConnectivityProtocolEvidenceMatrix
            {
                MatrixId = $"{suiteRunId}.matrix",
                ReportPath = Path.Combine(artifactDir, $"{suiteRunId}.protocol-matrix.json"),
                Inputs =
                [
                    new ConnectivityProtocolEvidenceInput
                    {
                        Role = "connectivity_probe_report",
                        Path = promotedTopologyPath,
                        Schema = "rusty.quest.connectivity_topology_probe.v1",
                        Status = "pass",
                    },
                ],
            };
            var suite = new ConnectivitySuiteRunReport
            {
                SuiteRunId = suiteRunId,
                ReportPath = Path.Combine(artifactDir, $"{suiteRunId}.suite.json"),
            };
            var method = typeof(HostessctlConnectivityService).GetMethod(
                    "RunDirectWifiProductMediaPlanAsync",
                    BindingFlags.NonPublic | BindingFlags.Static)
                ?? throw new InvalidOperationException("missing RunDirectWifiProductMediaPlanAsync method");
            var task = (Task<FileInfo>)method.Invoke(
                    null,
                    new object?[]
                    {
                        repoRoot,
                        suite,
                        matrix,
                        new List<FileInfo>(),
                        null,
                        new FileInfo(Path.Combine(reportDir, $"{suiteRunId}.projection.json")),
                        new FileInfo(Path.Combine(reportDir, $"{suiteRunId}.transport-gates.json")),
                        "C:\\Program Files\\Rusty Hostess\\HostessCompanion.Wpf.exe",
                        CancellationToken.None,
                    })!
                ?? throw new InvalidOperationException("direct-Wi-Fi product-media plan task was empty");
            planPath = task.GetAwaiter().GetResult();
    
            using var document = JsonDocument.Parse(File.ReadAllText(planPath.FullName));
            var root = document.RootElement;
            var artifacts = root.GetProperty("artifacts");
            Assert(artifacts.GetProperty("qcl082_report").GetString() == siblingProductMediaPath,
                "WPF acceptance-plan route must find promoted QCL-082 reports from the sibling Rusty Quest lifecycle target");
            Assert(root.GetProperty("readiness").GetProperty("product_tcp_media_over_direct_wifi_ready").GetBoolean(),
                "sibling promoted QCL-082 product-media evidence must clear the product media readiness dependency");
        }
        finally
        {
            Environment.SetEnvironmentVariable(
                HostessctlConnectivityService.LatestArtifactDirEnvironmentVariable,
                previousLatestArtifactDir);
            foreach (var path in new[]
            {
                promotedTopologyPath,
                siblingProductMediaPath,
                planPath?.FullName,
            })
            {
                if (!string.IsNullOrWhiteSpace(path) && File.Exists(path))
                {
                    File.Delete(path);
                }
            }
            if (Directory.Exists(questLifecycleDir))
            {
                Directory.Delete(questLifecycleDir, recursive: true);
            }
        }
    }
    

}
