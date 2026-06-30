using System.Reflection;
using System.Text.Json;
using HostessCompanion.Wpf.Models;
using HostessCompanion.Wpf.Services;
using HostessCompanion.Wpf.ViewModels;

var tests = new (string Name, Action Test)[]
{
    ("device-link projection promotes devices and transports", DeviceLinkProjectionPromotesDevicesAndTransports),
    ("session service reads device-link artifact", SessionServiceReadsDeviceLinkArtifact),
    ("session service exposes robust receipt wait arguments", SessionServiceExposesRobustReceiptWaitArguments),
    ("connectivity suite rows expose groups and metrics", ConnectivitySuiteRowsExposeGroupsAndMetrics),
    ("protocol matrix rows expose promotion gates", ProtocolMatrixRowsExposePromotionGates),
    ("protocol matrix rows expose latest promoted evidence", ProtocolMatrixRowsExposeLatestPromotedEvidence),
    ("companion report projection rows expose shared artifact", CompanionReportProjectionRowsExposeSharedArtifact),
    ("companion report projection projects topology probe rows", CompanionReportProjectionProjectsTopologyProbeRows),
    ("companion report projection rows expose transport coverage", CompanionReportProjectionRowsExposeTransportCoverage),
    ("transport gate rows expose next actions", TransportGateRowsExposeNextActions),
    ("connectivity service builds companion report projection artifact", ConnectivityServiceBuildsCompanionReportProjectionArtifact),
    ("firewall rows expose product verification", FirewallRowsExposeProductVerification),
    ("firewall rows expose elevation preflight", FirewallRowsExposeElevationPreflight),
    ("firewall service uses CLI admin handoff", FirewallServiceUsesCliAdminHandoff),
    ("firewall default names stay product scoped", FirewallDefaultNamesStayProductScoped),
    ("firewall QCL-082 profile plan uses CLI profile", FirewallQcl082ProfilePlanUsesCliProfile),
    ("operator actions map WPF commands to CLI routes", OperatorActionsMapWpfCommandsToCliRoutes),
    ("page viewmodels own WPF rows and selections", PageViewModelsOwnWpfRowsAndSelections),
    ("page viewmodels project backend reports", PageViewModelsProjectBackendReports),
};

var failed = 0;
foreach (var (name, test) in tests)
{
    try
    {
        test();
        Console.WriteLine($"PASS {name}");
    }
    catch (Exception ex)
    {
        failed++;
        Console.Error.WriteLine($"FAIL {name}: {ex}");
    }
}

return failed == 0 ? 0 : 1;

static void DeviceLinkProjectionPromotesDevicesAndTransports()
{
    var report = ReadFixture<DeviceLinkReport>("device-link-pass.json");
    var deviceRows = DeviceLinkOperatorProjection.BuildDeviceChecks(report);
    Assert(deviceRows.Any(row => row.CheckId == "device_link.identity" && row.Status == "pass"), "missing pass identity row");
    Assert(deviceRows.Any(row => row.Group == "runtime" && row.CheckId.Contains("runtime_subscriber")), "missing runtime subscriber row");
    Assert(deviceRows.Any(row => row.Group == "runtime" && row.CheckId.Contains("command_result")), "missing command result row");

    var transports = DeviceLinkOperatorProjection.BuildTransportDescriptors(report);
    Assert(transports.Any(row => row.TransportId == "tunnel.adb_forward.manifold_broker"), "missing ADB tunnel transport");
    Assert(transports.Any(row => row.TransportId == "broker.manifold.quest_forwarded"), "missing broker endpoint transport");
    var command = transports.Single(row => row.TransportId == "capability.command.hostess_makepad_bridge");
    Assert(command.RequiredEvidenceStages.Contains("applied"), "command capability must require applied evidence");
    Assert(transports.Any(row => row.TransportId == "capability.biosignal.lsl_clocked_samples"), "missing LSL stream capability");
}

static void SessionServiceReadsDeviceLinkArtifact()
{
    var service = new HostessctlSessionService();
    var session = new CompanionSessionReport
    {
        ArtifactRefs =
        [
            new SessionArtifactRef
            {
                Role = "device_link_report",
                Schema = "rusty.quest.device_link.v1",
                Path = "tests/HostessCompanion.Wpf.Tests/Fixtures/device-link-pass.json",
            },
        ],
    };
    var report = service.TryReadDeviceLinkReport(session);
    Assert(report is not null, "expected device-link report");
    Assert(report!.Status == "pass", "expected pass report");
    Assert(report.Tunnels.Count == 1, "expected tunnel");
}

static void SessionServiceExposesRobustReceiptWaitArguments()
{
    var arguments = HostessctlSessionService.SessionReliabilityArguments;
    AssertArgument(arguments, "--wait-seconds", "30");
    AssertArgument(arguments, "--fallback-wait-seconds", "30");
    AssertArgument(arguments, "--authority-wait-seconds", "30");
    AssertArgument(arguments, "--broker-process-wait-seconds", "20");
    AssertArgument(arguments, "--makepad-process-wait-seconds", "20");
    AssertArgument(arguments, "--socket-wait-seconds", "20");
    AssertArgument(arguments, "--launch-settle-seconds", "8");
    AssertArgument(arguments, "--runtime-subscriber-retry-count", "8");
    AssertArgument(arguments, "--runtime-subscriber-retry-wait-seconds", "2");
}

static void ConnectivitySuiteRowsExposeGroupsAndMetrics()
{
    var metrics = JsonSerializer.SerializeToElement(new
    {
        rtt_ms = 12,
        samples = 3,
    });
    var report = new ConnectivitySuiteRunReport
    {
        Status = "warn",
        SuiteId = "suite",
        SuiteRunId = "suite-run",
        Mode = "fixture",
        SuiteDescriptorPath = "target/suite.json",
        EnvironmentSnapshot = JsonSerializer.SerializeToElement(new { network = "fixture" }),
        GroupedResults =
        [
            new ConnectivitySuiteGroupResult
            {
                GroupId = "group.protocol",
                Phase = "protocol",
                Status = "pass",
                SlotCount = 1,
                PassCount = 1,
                SlotIds = ["suite.qcl080"],
            },
        ],
        SlotResults =
        [
            new ConnectivitySuiteSlotResult
            {
                SlotId = "suite.qcl080",
                ProbeId = "QCL-080",
                Phase = "protocol",
                Status = "pass",
                ReportStatus = "pass",
                ValidationStatus = "pass",
                ReportPath = "target/qcl080.json",
                Metrics = metrics,
            },
        ],
    };

    var rows = ConnectivityRows.ForSuiteReport(report);
    Assert(rows[0].Name == "quest.device_link.install_environment_suite_run", "missing suite summary row");
    Assert(rows.Any(row => row.Name == "group.protocol"), "missing protocol group row");
    Assert(rows.Any(row => row.Name == "suite.qcl080" && row.Evidence.Contains("rtt_ms=12", StringComparison.Ordinal)), "missing metric summary");
    Assert(ConnectivityRows.StatusFromRows(rows) == "warn", "suite row warning must remain visible");
}

static void ProtocolMatrixRowsExposePromotionGates()
{
    var matrix = new ConnectivityProtocolEvidenceMatrix
    {
        Status = "warn",
        MatrixId = "matrix-fixture",
        ReportPath = "target/protocol-matrix.json",
        Summary = JsonSerializer.SerializeToElement(new
        {
            all_required_data_protocols_promoted = false,
            pending_required_probe_ids = new[] { "QCL-084" },
        }),
        Rows =
        [
            new ConnectivityProtocolEvidenceRow
            {
                CapabilityId = "capability.protocol.zeromq_native_rust",
                ProbeId = "QCL-084",
                TransportKind = "zeromq",
                SemanticFamily = "generic_data_protocol",
                AuthorityOwner = "rusty.manifold.transport",
                RequiredForFoldIn = true,
                Status = "candidate",
                PromotionState = "candidate",
                PromotionAllowed = false,
                EvidenceTier = "host_loopback",
                PromotionGate = "broker-owned or Quest-runtime evidence required",
                MissingGates =
                [
                    "gate.qcl084.quest_runtime_or_broker_owned",
                    "gate.qcl084.promotion_allowed",
                ],
                GateResults =
                [
                    new ConnectivityProtocolEvidenceGate
                    {
                        GateId = "gate.qcl084.quest_runtime_or_broker_owned",
                        Status = "missing",
                        Evidence = "evidence_tier=host_loopback",
                    },
                    new ConnectivityProtocolEvidenceGate
                    {
                        GateId = "gate.qcl084.report_passed",
                        Status = "satisfied",
                        Evidence = "report status=pass",
                    },
                ],
                Measurements = JsonSerializer.SerializeToElement(new { zeromq_messages_received = 5 }),
            },
        ],
    };

    var rows = ConnectivityRows.ForProtocolEvidenceMatrix(matrix);

    Assert(rows[0].Name == "quest.device_link.protocol_evidence_matrix", "missing matrix summary row");
    Assert(rows.Any(row => row.Name == "QCL-084.zeromq" && row.Status == "candidate"),
        "missing QCL-084 protocol row");
    Assert(rows.Any(row => row.Name == "gate.qcl084.quest_runtime_or_broker_owned" && row.Status == "warn"),
        "missing gate row");
    Assert(rows.Any(row => row.IssueCodes.Contains("hostess.issue.protocol_evidence_matrix.required_protocol_not_promoted")),
        "missing required protocol warning");
    Assert(ConnectivityRows.StatusFromRows(rows) == "warn", "protocol matrix warnings must remain visible");
}

static void ProtocolMatrixRowsExposeLatestPromotedEvidence()
{
    var matrix = new ConnectivityProtocolEvidenceMatrix
    {
        Status = "pass",
        MatrixId = "matrix-latest",
        ReportPath = "target/protocol-matrix-latest.json",
        Summary = JsonSerializer.SerializeToElement(new
        {
            all_required_data_protocols_promoted = true,
            pending_required_probe_ids = Array.Empty<string>(),
        }),
        Rows =
        [
            PromotedProtocolRow("capability.biosignal.lsl_clocked_samples", "QCL-081", "lsl", "broker_owned"),
            PromotedProtocolRow("capability.protocol.osc_low_rate_messages", "QCL-083", "osc", "quest_runtime"),
            PromotedProtocolRow("capability.protocol.zeromq_native_rust", "QCL-084", "zeromq", "broker_owned"),
        ],
    };

    var rows = ConnectivityRows.ForProtocolEvidenceMatrix(matrix);

    Assert(rows.Any(row => row.Name == "QCL-081.lsl"
        && row.Status == "usable"
        && row.Evidence.Contains("tier=broker_owned", StringComparison.Ordinal)
        && row.Evidence.Contains("promotion=promoted", StringComparison.Ordinal)),
        "missing promoted QCL-081 evidence row");
    Assert(rows.Any(row => row.Name == "QCL-083.osc"
        && row.Status == "usable"
        && row.Evidence.Contains("tier=quest_runtime", StringComparison.Ordinal)),
        "missing promoted QCL-083 evidence row");
    Assert(rows.Any(row => row.Name == "QCL-084.zeromq"
        && row.Status == "usable"
        && row.Evidence.Contains("tier=broker_owned", StringComparison.Ordinal)),
        "missing promoted QCL-084 evidence row");
    Assert(rows.Any(row => row.Name == "gate.qcl081.promotion_allowed" && row.Status == "pass"),
        "missing satisfied promoted gate row");
    Assert(ConnectivityRows.StatusFromRows(rows) == "pass", "promoted protocol matrix should project pass");
}

static void CompanionReportProjectionRowsExposeSharedArtifact()
{
    var projection = ReadFixture<CompanionReportProjection>("companion-report-projection-pass.json");
    projection.ReportPath = "target/companion-report/projection.fixture.wpf.json";

    var rows = ConnectivityRows.ForCompanionReportProjection(projection);

    Assert(rows[0].Name == "hostess.companion_report_projection", "missing projection summary row");
    Assert(rows.Any(row => row.Name == "projection.source.device_link_report.source.device_link_report.1"
        && row.Evidence.Contains("rusty.quest.device_link.v1", StringComparison.Ordinal)),
        "missing device-link source artifact row");
    Assert(rows.Any(row =>
            row.Name == "protocol_matrix.row.QCL-081.capability.biosignal.lsl_clocked_samples"
            && row.Status == "usable"
            && row.Evidence.Contains("tier=broker_owned", StringComparison.Ordinal)
            && row.Evidence.Contains("authority=rusty.manifold.transport", StringComparison.Ordinal)
            && row.Notes.Contains("fixtures/companion/protocol-matrix-promoted.json", StringComparison.Ordinal)),
        "missing shared projection row for broker-owned QCL-081");
    Assert(ConnectivityRows.StatusFromRows(rows) == "pass", "projection fixture should project pass");
}

static void CompanionReportProjectionProjectsTopologyProbeRows()
{
    var projection = ReadFixture<CompanionReportProjection>("companion-report-topology-projection.json");
    projection.ReportPath = "target/companion-report/projection.topology.wpf.json";

    var rows = ConnectivityRows.ForCompanionReportProjection(projection);

    Assert(rows.Any(row => row.Name == "projection.source.connectivity_probe_report.source.connectivity_probe_report.1"
        && row.Evidence.Contains("rusty.quest.connectivity_topology_probe.v1", StringComparison.Ordinal)),
        "missing connectivity-probe source row");
    Assert(rows.Any(row =>
            row.Name == "connectivity_probe.topology.QCL-030"
            && row.Status == "candidate"
            && row.Evidence.Contains("local_only_hotspot", StringComparison.Ordinal)
            && row.IssueCodes.Contains("hostess.issue.connectivity_probe.experimental_topology")),
        "missing topology candidate row");
    Assert(rows.Any(row =>
            row.Name == "connectivity_probe.promotion.QCL-030"
            && row.Status == "candidate"
            && row.IssueCodes.Contains("gate.qcl-030.promotion_allowed")),
        "missing topology promotion gate row");
    Assert(ConnectivityRows.StatusFromRows(rows) == "planned",
        "topology projection must stay planned until live evidence promotes it");
}

static void CompanionReportProjectionRowsExposeTransportCoverage()
{
    var projection = new CompanionReportProjection
    {
        Status = "pass",
        ProjectionId = "projection.transport-coverage",
        SourceArtifacts =
        [
            new CompanionReportProjectionSource
            {
                SourceId = "source.protocol_evidence_matrix.1",
                Role = "protocol_evidence_matrix",
                RequestedRole = "protocol_evidence_matrix",
                Schema = "rusty.quest.device_link.protocol_evidence_matrix.v1",
                Status = "pass",
                Path = "target/protocol-matrix.json",
            },
        ],
        Rows =
        [
            new CompanionReportProjectionRow
            {
                RowId = "transport_coverage.summary",
                Section = "transport_coverage",
                Kind = "transport_coverage_summary",
                Label = "Transport coverage",
                Status = "candidate",
                AuthorityOwner = "source_artifacts",
                Evidence = "families=tcp, websocket, wifi_direct; topologies=wifi_direct; probes=QCL-010, QCL-040",
                Notes = "websocket=device_link.broker; tcp=connectivity_probe.check.QCL-010; wifi_direct=connectivity_probe.topology.QCL-040",
                SourceArtifact = "source.protocol_evidence_matrix.1",
                Details = JsonSerializer.SerializeToElement(new
                {
                    explicit_terms = new
                    {
                        websocket = true,
                        tcp = true,
                        wifi_direct = true,
                    },
                    term_gates = new
                    {
                        websocket = new
                        {
                            included = true,
                            scope = "manifold_command_session_receipts",
                            promotion_boundary = "Current WebSocket coverage is the Manifold command/session receipt route, not a generic WebSocket data-plane slot.",
                        },
                        tcp = new
                        {
                            included = true,
                            scope = "qcl010_qcl011_echo_and_qcl082_tcp_binary_media",
                            promotion_boundary = "TCP visibility covers topology echo and QCL-082 binary media; product TCP over direct Wi-Fi needs a live topology/listener gate.",
                        },
                        wifi_direct = new
                        {
                            included = true,
                            scope = "qcl040_qcl041_topology_evidence",
                            promotion_boundary = "Wi-Fi Direct is topology evidence and remains experimental until live peer discovery, group lifecycle, socket exchange, and cleanup evidence promote it.",
                        },
                    },
                    remaining_live_gates = new object[]
                    {
                        new
                        {
                            gate_id = "transport.general_websocket_capability",
                            status = "not_in_current_scope",
                        },
                        new
                        {
                            gate_id = "transport.direct_wifi_live_topology",
                            status = "pending_live_evidence",
                        },
                        new
                        {
                            gate_id = "transport.product_tcp_media_over_direct_wifi",
                            status = "pending_live_evidence",
                        },
                    },
                }),
            },
        ],
    };

    var rows = ConnectivityRows.ForCompanionReportProjection(projection);
    var coverage = rows.Single(row => row.Name == "transport_coverage.summary");
    Assert(coverage.Evidence.Contains("websocket", StringComparison.Ordinal),
        "coverage row must keep WebSocket visible");
    Assert(coverage.Evidence.Contains("tcp", StringComparison.Ordinal),
        "coverage row must keep TCP visible");
    Assert(coverage.Evidence.Contains("wifi_direct", StringComparison.Ordinal),
        "coverage row must keep Wi-Fi Direct visible");
    var termGates = coverage.Observed.GetProperty("Details").GetProperty("term_gates");
    Assert(termGates.GetProperty("websocket").GetProperty("scope").GetString() == "manifold_command_session_receipts",
        "coverage details must scope WebSocket to Manifold command/session receipts");
    Assert(termGates.GetProperty("tcp").GetProperty("scope").GetString() == "qcl010_qcl011_echo_and_qcl082_tcp_binary_media",
        "coverage details must scope TCP to topology echo and QCL-082 binary media");
    Assert(termGates.GetProperty("wifi_direct").GetProperty("scope").GetString() == "qcl040_qcl041_topology_evidence",
        "coverage details must scope Wi-Fi Direct to topology evidence");
    Assert(ConnectivityRows.StatusFromRows(rows) == "planned",
        "candidate direct-Wi-Fi coverage must keep the projection planned");
}

static void ConnectivityServiceBuildsCompanionReportProjectionArtifact()
{
    var run = new HostessctlConnectivityService()
        .RunProtocolMatrixProjectionAsync(
            serial: "",
            program: "",
            protocol: "UDP",
            portText: "18767",
            cancellationToken: CancellationToken.None)
        .GetAwaiter()
        .GetResult();

    Assert(run.Suite.ReportPath.EndsWith(".json", StringComparison.Ordinal),
        "suite report path must be attached");
    Assert(run.Matrix.ReportPath.EndsWith(".protocol-matrix.json", StringComparison.Ordinal),
        "matrix report path must be attached");
    Assert(File.Exists(run.Projection.ReportPath), "projection report must be written");
    Assert(File.Exists(run.TransportGates.ReportPath), "transport gate report must be written");
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

static void TransportGateRowsExposeNextActions()
{
    var report = new CompanionTransportGateReport
    {
        Schema = "rusty.hostess.companion.transport_gate_report.v1",
        Status = "warn",
        ReportId = "transport-gates.test",
        Authority = new CompanionTransportGateAuthority
        {
            ProjectionOnly = true,
            AcceptanceOwner = "source_projection",
        },
        SourceProjection = new CompanionTransportGateSourceProjection
        {
            ProjectionId = "projection.test",
            Schema = "rusty.hostess.companion.report_projection.v1",
            Path = "target/companion-report/projection.json",
        },
        Summary = new CompanionTransportGateSummary
        {
            RemainingGateCount = 3,
            RemainingGateIds =
            [
                "transport.direct_wifi_live_topology",
                "transport.product_tcp_media_over_direct_wifi",
                "transport.product_tcp_media_listener_firewall",
            ],
            TermGateCount = 1,
            TermGateIds = ["wifi_direct"],
        },
        OperatorNextActions = new CompanionTransportGateOperatorActions
        {
            Shell = "powershell",
            Cwd = "<rusty-hostess-root>",
            GateCount = 2,
            Policy = "Hostess-owned CLI routes only",
            Gates =
            [
                new CompanionTransportGateActionSummary
                {
                    GateId = "transport.direct_wifi_live_topology",
                    NextActionIds =
                    [
                        "write_direct_wifi_product_media_acceptance_plan",
                        "plan_qcl040_wifi_direct_lifecycle",
                        "plan_qcl041_wifi_direct_lifecycle",
                        "run_qcl041_live_wifi_direct_preflight",
                        "normalize_qcl040_wifi_direct_lifecycle_report",
                        "normalize_qcl041_wifi_direct_lifecycle_report",
                    ],
                },
                new CompanionTransportGateActionSummary
                {
                    GateId = "transport.product_tcp_media_over_direct_wifi",
                    NextActionIds =
                    [
                        "write_qcl082_product_media_direct_wifi_plan",
                        "write_direct_wifi_product_media_acceptance_plan",
                        "write_qcl082_media_stream_start_source_request",
                        "run_qcl082_media_stream_start_source",
                        "validate_qcl082_media_stream_runtime_status",
                        "capture_rmanvid1_over_promoted_direct_wifi",
                        "promote_qcl082_rmanvid1_capture",
                    ],
                },
                new CompanionTransportGateActionSummary
                {
                    GateId = "transport.product_tcp_media_listener_firewall",
                    NextActionIds = ["verify_qcl082_product_firewall_rule"],
                },
            ],
        },
        TermGates = new Dictionary<string, JsonElement>
        {
            ["wifi_direct"] = JsonSerializer.SerializeToElement(new
            {
                scope = "qcl040_qcl041_topology_evidence",
            }),
        },
        RemainingLiveGates =
        [
            new CompanionTransportGate
            {
                GateId = "transport.direct_wifi_live_topology",
                Status = "pending_live_evidence",
                Evidence = "needs live peer lifecycle",
                NextActions =
                [
                    new CompanionTransportGateNextAction
                    {
                        ActionId = "plan_qcl041_wifi_direct_lifecycle",
                        Label = "Write QCL-041 lifecycle execution plan",
                        AuthorityOwner = "tools.hostessctl.connectivity_topology_lifecycle_plan",
                        AcceptanceArtifacts =
                        [
                            "target\\connectivity-probe\\qcl041-wifi-direct-lifecycle-plan.json",
                        ],
                        Command = new CompanionTransportGateNextActionCommand
                        {
                            Shell = "powershell",
                            Command = "python tools\\hostessctl\\hostessctl.py connectivity-probe wifi-direct-lifecycle-plan --probe-id QCL-041 --out target\\connectivity-probe\\qcl041-wifi-direct-lifecycle-plan.json",
                        },
                    },
                    new CompanionTransportGateNextAction
                    {
                        ActionId = "write_direct_wifi_product_media_acceptance_plan",
                        Label = "Write direct-Wi-Fi product-media acceptance plan",
                        AuthorityOwner = "tools.hostessctl.connectivity_direct_wifi_product_media_plan",
                        AcceptanceArtifacts =
                        [
                            "target\\connectivity-probe\\direct-wifi-product-media-acceptance-plan.json",
                        ],
                        Command = new CompanionTransportGateNextActionCommand
                        {
                            Shell = "powershell",
                            Command = "python tools\\hostessctl\\hostessctl.py connectivity-probe direct-wifi-product-media-plan --out target\\connectivity-probe\\direct-wifi-product-media-acceptance-plan.json --qcl041-topology-report target\\connectivity-probe\\qcl041-live-wifi-direct-lifecycle.json --firewall-report target\\connectivity-probe\\qcl082-tcp-firewall-admin-handoff-verify.json --qcl082-report target\\connectivity-probe\\qcl082-rmanvid1-receiver-capture.json",
                        },
                    },
                    new CompanionTransportGateNextAction
                    {
                        ActionId = "run_qcl041_live_wifi_direct_preflight",
                        Label = "Run QCL-041 live preflight",
                        RequiresQuestLease = true,
                        RequiresAdbServerLifecycleLease = false,
                        Command = new CompanionTransportGateNextActionCommand
                        {
                            Shell = "powershell",
                            Command = "python tools\\hostessctl\\hostessctl.py connectivity-probe run --mode live --probe-id QCL-041 --adb S:\\Work\\tools\\Android\\windows-sdk\\platform-tools\\adb.exe --serial '<quest-serial>'",
                        },
                        Lease = new CompanionTransportGateNextActionLease
                        {
                            Manager = "Agent Board",
                            Resource = "quest:<quest-serial>",
                            Duration = "45m",
                            ReleaseCommand = "& 'S:\\Work\\agent-bureau\\scripts\\agent-board.ps1' release '<quest-lease-id>' --result done",
                        },
                    },
                    new CompanionTransportGateNextAction
                    {
                        ActionId = "normalize_qcl040_wifi_direct_lifecycle_report",
                        Label = "Build QCL-040 lifecycle topology report",
                        AuthorityOwner = "tools.hostessctl.connectivity_topology_lifecycle",
                        ClearsGateWhenAccepted = true,
                        AcceptanceArtifacts =
                        [
                            "target\\connectivity-probe\\qcl040-live-wifi-direct-lifecycle.json",
                        ],
                        Command = new CompanionTransportGateNextActionCommand
                        {
                            Shell = "powershell",
                            Command = "python tools\\hostessctl\\hostessctl.py connectivity-probe run --mode fixture --probe-id QCL-040 --wifi-direct-lifecycle-report '<wifi-direct-lifecycle-report>' --out target\\connectivity-probe\\qcl040-live-wifi-direct-lifecycle.json --fail-on-error",
                        },
                    },
                    new CompanionTransportGateNextAction
                    {
                        ActionId = "normalize_qcl041_wifi_direct_lifecycle_report",
                        Label = "Build QCL-041 lifecycle topology report",
                        AuthorityOwner = "tools.hostessctl.connectivity_topology_lifecycle",
                        ClearsGateWhenAccepted = true,
                        AcceptanceArtifacts =
                        [
                            "target\\connectivity-probe\\qcl041-live-wifi-direct-lifecycle.json",
                        ],
                        Command = new CompanionTransportGateNextActionCommand
                        {
                            Shell = "powershell",
                            Command = "python tools\\hostessctl\\hostessctl.py connectivity-probe run --mode fixture --probe-id QCL-041 --wifi-direct-lifecycle-report '<wifi-direct-lifecycle-report>' --out target\\connectivity-probe\\qcl041-live-wifi-direct-lifecycle.json --fail-on-error",
                        },
                    },
                ],
            },
            new CompanionTransportGate
            {
                GateId = "transport.product_tcp_media_over_direct_wifi",
                Status = "pending_live_evidence",
                Evidence = "needs product TCP media over promoted direct Wi-Fi",
                NextActions =
                [
                    new CompanionTransportGateNextAction
                    {
                        ActionId = "write_qcl082_product_media_direct_wifi_plan",
                        Label = "Write QCL-082 product media plan",
                        AuthorityOwner = "tools.hostessctl.connectivity_media_product_plan",
                        AcceptanceArtifacts =
                        [
                            "target\\connectivity-probe\\qcl082-product-media-direct-wifi-plan.json",
                        ],
                        Command = new CompanionTransportGateNextActionCommand
                        {
                            Label = "Write QCL-082 product media plan",
                            Shell = "powershell",
                            Command = "python tools\\hostessctl\\hostessctl.py connectivity-probe qcl082-product-media-plan --out target\\connectivity-probe\\qcl082-product-media-direct-wifi-plan.json --promoted-topology-report '<promoted-qcl040-or-qcl041-topology-report>' --firewall-report target\\connectivity-probe\\qcl082-tcp-firewall-admin-handoff-verify.json",
                        },
                    },
                    new CompanionTransportGateNextAction
                    {
                        ActionId = "write_direct_wifi_product_media_acceptance_plan",
                        Label = "Write direct-Wi-Fi product-media acceptance plan",
                        AuthorityOwner = "tools.hostessctl.connectivity_direct_wifi_product_media_plan",
                        AcceptanceArtifacts =
                        [
                            "target\\connectivity-probe\\direct-wifi-product-media-acceptance-plan.json",
                        ],
                        Command = new CompanionTransportGateNextActionCommand
                        {
                            Label = "Write direct-Wi-Fi product-media acceptance plan",
                            Shell = "powershell",
                            Command = "python tools\\hostessctl\\hostessctl.py connectivity-probe direct-wifi-product-media-plan --out target\\connectivity-probe\\direct-wifi-product-media-acceptance-plan.json --qcl041-topology-report target\\connectivity-probe\\qcl041-live-wifi-direct-lifecycle.json --firewall-report target\\connectivity-probe\\qcl082-tcp-firewall-admin-handoff-verify.json --qcl082-report target\\connectivity-probe\\qcl082-rmanvid1-receiver-capture.json",
                        },
                    },
                    new CompanionTransportGateNextAction
                    {
                        ActionId = "write_qcl082_media_stream_start_source_request",
                        Label = "Write QCL-082 start_source request",
                        AuthorityOwner = "tools.hostessctl.bridge_command_routes",
                        AcceptanceArtifacts =
                        [
                            "target\\connectivity-probe\\media-stream-start-source.request.json",
                        ],
                        Command = new CompanionTransportGateNextActionCommand
                        {
                            Label = "Write QCL-082 start_source request",
                            Shell = "powershell",
                            Command = "python tools\\hostessctl\\hostessctl.py emit-bridge-command-request --bridge-command command.media_stream.start_source --request-id request.hostess.qcl082.media_stream.start_source --evidence-id evidence.hostess.qcl082.media_stream.start_source --route-id bridge_route.command.websocket.applied --required-stage sent --required-stage transport_ok --required-stage authority_accepted --out target\\connectivity-probe\\media-stream-start-source.request.json",
                        },
                    },
                    new CompanionTransportGateNextAction
                    {
                        ActionId = "run_qcl082_media_stream_start_source",
                        Label = "Run QCL-082 media-stream start_source",
                        AuthorityOwner = "tools.hostessctl.bridge_command_live_android_routes",
                        RequiresQuestLease = true,
                        MutatesHost = true,
                        MutatesDevice = true,
                        DependsOn =
                        [
                            "transport.direct_wifi_live_topology",
                            "transport.product_tcp_media_listener_firewall",
                        ],
                        AcceptanceArtifacts =
                        [
                            "target\\connectivity-probe\\media-stream-start-source.request.json",
                            "target\\connectivity-probe\\media-stream-start-source.bridge-evidence.json",
                            "target\\connectivity-probe\\media-stream-start-source.live-android-execution.json",
                            "target\\connectivity-probe\\media-stream-start-source.validation-report.json",
                        ],
                        Command = new CompanionTransportGateNextActionCommand
                        {
                            Label = "Run QCL-082 media-stream start_source",
                            Shell = "powershell",
                            Command = "python tools\\hostessctl\\hostessctl.py run-bridge-command-live-android --input target\\connectivity-probe\\media-stream-start-source.request.json --out target\\connectivity-probe\\media-stream-start-source.bridge-evidence.json --execution-out target\\connectivity-probe\\media-stream-start-source.live-android-execution.json --validation-out target\\connectivity-probe\\media-stream-start-source.validation-report.json --adb S:\\Work\\tools\\Android\\windows-sdk\\platform-tools\\adb.exe --serial '<quest-serial>'",
                        },
                        Lease = new CompanionTransportGateNextActionLease
                        {
                            Manager = "Agent Board",
                            Resource = "quest:<quest-serial>",
                            Duration = "45m",
                            ReleaseCommand = "& 'S:\\Work\\agent-bureau\\scripts\\agent-board.ps1' release '<quest-lease-id>' --result done",
                        },
                    },
                    new CompanionTransportGateNextAction
                    {
                        ActionId = "validate_qcl082_media_stream_runtime_status",
                        Label = "Validate QCL-082 media runtime status",
                        AuthorityOwner = "tools.hostessctl.connectivity_media",
                        AcceptanceArtifacts =
                        [
                            "target\\connectivity-probe\\qcl082-media-stream-runtime-status.json",
                        ],
                        Command = new CompanionTransportGateNextActionCommand
                        {
                            Label = "Validate QCL-082 media runtime status",
                            Shell = "powershell",
                            Command = "python tools\\hostessctl\\hostessctl.py connectivity-probe run --mode fixture --probe-id QCL-082 --media-stream-runtime-status target\\connectivity-probe\\media-stream-start-source.live-android-execution.json --out target\\connectivity-probe\\qcl082-media-stream-runtime-status.json --fail-on-error",
                        },
                    },
                    new CompanionTransportGateNextAction
                    {
                        ActionId = "capture_rmanvid1_over_promoted_direct_wifi",
                        Label = "Capture RMANVID1 receiver counters",
                        AuthorityOwner = "tools.hostessctl.connectivity_media_receiver",
                        RequiresQuestLease = true,
                        MutatesDevice = true,
                        DependsOn =
                        [
                            "transport.direct_wifi_live_topology",
                            "transport.product_tcp_media_listener_firewall",
                        ],
                        AcceptanceArtifacts =
                        [
                            "target\\connectivity-probe\\media-stream.rmanvid1",
                            "target\\connectivity-probe\\media-stream-receiver-sidecar.json",
                            "target\\connectivity-probe\\media-stream-receiver-result.json",
                        ],
                        Command = new CompanionTransportGateNextActionCommand
                        {
                            Label = "Capture RMANVID1 receiver counters",
                            Shell = "powershell",
                            Command = "python tools\\hostessctl\\hostessctl.py connectivity-probe rmanvid1-receiver-capture --runtime-status target\\connectivity-probe\\media-stream-start-source.live-android-execution.json --topology-report '<promoted-qcl040-or-qcl041-topology-report>' --firewall-report target\\connectivity-probe\\qcl082-tcp-firewall-admin-handoff-verify.json",
                        },
                        Lease = new CompanionTransportGateNextActionLease
                        {
                            Manager = "Agent Board",
                            Resource = "quest:<quest-serial>",
                            Duration = "45m",
                            ReleaseCommand = "& 'S:\\Work\\agent-bureau\\scripts\\agent-board.ps1' release '<quest-lease-id>' --result done",
                        },
                    },
                    new CompanionTransportGateNextAction
                    {
                        ActionId = "promote_qcl082_rmanvid1_capture",
                        Label = "Build QCL-082 product media report",
                        AuthorityOwner = "tools.hostessctl.connectivity_probe",
                        ClearsGateWhenAccepted = true,
                        AcceptanceArtifacts =
                        [
                            "target\\connectivity-probe\\qcl082-rmanvid1-receiver-capture.json",
                        ],
                        Command = new CompanionTransportGateNextActionCommand
                        {
                            Label = "Build QCL-082 product media report",
                            Shell = "powershell",
                            Command = "python tools\\hostessctl\\hostessctl.py connectivity-probe run --mode fixture --probe-id QCL-082 --media-stream-rmanvid1-capture target\\connectivity-probe\\media-stream.rmanvid1 --media-stream-receiver-sidecar target\\connectivity-probe\\media-stream-receiver-sidecar.json --media-stream-runtime-status target\\connectivity-probe\\media-stream-start-source.live-android-execution.json --media-stream-topology-report '<promoted-qcl040-or-qcl041-topology-report>' --media-stream-firewall-report target\\connectivity-probe\\qcl082-tcp-firewall-admin-handoff-verify.json --out target\\connectivity-probe\\qcl082-rmanvid1-receiver-capture.json --fail-on-error",
                        },
                    },
                ],
            },
            new CompanionTransportGate
            {
                GateId = "transport.product_tcp_media_listener_firewall",
                Status = "pending_live_evidence",
                Evidence = "needs product listener firewall rule",
                NextActions =
                [
                    new CompanionTransportGateNextAction
                    {
                        ActionId = "verify_qcl082_product_firewall_rule",
                        Label = "Verify product listener rule",
                        RequiresElevation = true,
                        Command = new CompanionTransportGateNextActionCommand
                        {
                            Shell = "powershell",
                            Command = "python tools\\hostessctl\\hostessctl.py connectivity-probe windows-firewall-rule --action verify --rule-profile qcl-082-rmanvid1-media",
                        },
                    },
                ],
            },
        ],
    };

    var rows = ConnectivityRows.ForTransportGateReport(report);

    Assert(rows.Any(row => row.Name == "hostess.companion_transport_gates" && row.Status == "warn"),
        "transport gate report summary row must stay visible");
    Assert(rows.Any(row =>
            row.Name == "transport_gates.operator_next_actions"
            && row.Evidence.Contains("shell=powershell", StringComparison.Ordinal)),
        "transport gate rows must include the operator next-action summary");
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
            && row.Evidence.Contains("--qcl082-report", StringComparison.Ordinal)),
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
            && row.Evidence.Contains("--promoted-topology-report '<promoted-qcl040-or-qcl041-topology-report>'", StringComparison.Ordinal)),
        "product media plan action must render the CLI-owned direct-Wi-Fi media plan artifact");
    Assert(rows.Any(row =>
            row.Name == "transport.product_tcp_media_over_direct_wifi.write_direct_wifi_product_media_acceptance_plan"
            && row.Notes.Contains("authority_owner=tools.hostessctl.connectivity_direct_wifi_product_media_plan", StringComparison.Ordinal)
            && row.Notes.Contains("acceptance_artifacts=target\\connectivity-probe\\direct-wifi-product-media-acceptance-plan.json", StringComparison.Ordinal)
            && row.Evidence.Contains("direct-wifi-product-media-plan", StringComparison.Ordinal)
            && row.Evidence.Contains("--firewall-report", StringComparison.Ordinal)),
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
            row.Name == "transport.product_tcp_media_over_direct_wifi.capture_rmanvid1_over_promoted_direct_wifi"
            && row.Notes.Contains("authority_owner=tools.hostessctl.connectivity_media_receiver", StringComparison.Ordinal)
            && row.Notes.Contains("requires_quest_lease=True", StringComparison.Ordinal)
            && row.Notes.Contains("mutates_device=True", StringComparison.Ordinal)
            && row.Notes.Contains("depends_on=transport.direct_wifi_live_topology,transport.product_tcp_media_listener_firewall", StringComparison.Ordinal)
            && row.Notes.Contains("acceptance_artifacts=target\\connectivity-probe\\media-stream.rmanvid1,target\\connectivity-probe\\media-stream-receiver-sidecar.json,target\\connectivity-probe\\media-stream-receiver-result.json", StringComparison.Ordinal)
            && row.Evidence.Contains("--runtime-status target\\connectivity-probe\\media-stream-start-source.live-android-execution.json", StringComparison.Ordinal)),
        "product media next action must show dependency and acceptance-artifact evidence");
    Assert(rows.Any(row =>
            row.Name == "transport.product_tcp_media_over_direct_wifi.promote_qcl082_rmanvid1_capture"
            && row.Notes.Contains("authority_owner=tools.hostessctl.connectivity_probe", StringComparison.Ordinal)
            && row.Notes.Contains("clears_gate=True", StringComparison.Ordinal)
            && row.Evidence.Contains("--media-stream-runtime-status target\\connectivity-probe\\media-stream-start-source.live-android-execution.json", StringComparison.Ordinal)),
        "product media promotion action must render the QCL-082 fold-in route");
    Assert(rows.Any(row =>
            row.Name == "transport.product_tcp_media_listener_firewall.verify_qcl082_product_firewall_rule"
            && row.Notes.Contains("requires_elevation=True", StringComparison.Ordinal)
            && row.Evidence.Contains("--rule-profile qcl-082-rmanvid1-media", StringComparison.Ordinal)),
        "firewall next action must show elevation and product rule profile");
}

static void FirewallRowsExposeProductVerification()
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

static void FirewallRowsExposeElevationPreflight()
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

static void FirewallServiceUsesCliAdminHandoff()
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

static void FirewallDefaultNamesStayProductScoped()
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

static void FirewallQcl082ProfilePlanUsesCliProfile()
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

static void OperatorActionsMapWpfCommandsToCliRoutes()
{
    var commandProperties = typeof(MainWindowViewModel)
        .GetProperties()
        .Where(property => property.PropertyType == typeof(AsyncRelayCommand))
        .Select(property => property.Name)
        .Order(StringComparer.Ordinal)
        .ToArray();
    var mappedProperties = OperatorActionCatalog.All
        .Select(action => action.UiCommandProperty)
        .Order(StringComparer.Ordinal)
        .ToArray();

    Assert(
        commandProperties.SequenceEqual(mappedProperties),
        "every WPF command property must have an operator action descriptor");
    foreach (var action in OperatorActionCatalog.All)
    {
        Assert(action.ActionId.StartsWith("wpf.", StringComparison.Ordinal), "action id must be WPF scoped");
        Assert(!string.IsNullOrWhiteSpace(action.CliRoute), $"missing CLI route for {action.ActionId}");
        Assert(!action.CliRoute.Contains("button", StringComparison.OrdinalIgnoreCase),
            $"CLI route must not be UI-only for {action.ActionId}");
        Assert(!string.IsNullOrWhiteSpace(action.EvidenceArtifact), $"missing evidence artifact for {action.ActionId}");
        Assert(!string.IsNullOrWhiteSpace(action.TestCoverage), $"missing test coverage for {action.ActionId}");
    }
    Assert(
        OperatorActionCatalog.All.Any(action =>
            action.UiCommandProperty == "RunSessionCommand"
            && action.CliRoute.Contains("companion-session run", StringComparison.Ordinal)
            && action.CliRoute.Contains("--wait-seconds 30", StringComparison.Ordinal)
            && action.CliRoute.Contains("--fallback-wait-seconds 30", StringComparison.Ordinal)
            && action.CliRoute.Contains("--runtime-subscriber-retry-count 8", StringComparison.Ordinal)
            && action.CliRoute.Contains("--runtime-subscriber-retry-wait-seconds 2", StringComparison.Ordinal)),
        "session run must advertise the robust runtime receipt CLI route");
    Assert(
        OperatorActionCatalog.All.Any(action =>
            action.UiCommandProperty == "LoadSessionHistoryCommand"
            && action.CliRoute.Contains("companion-session history", StringComparison.Ordinal)),
        "session history must stay backed by the companion-session history CLI route");
    var protocolMatrixAction = OperatorActionCatalog.All.Single(action =>
        action.UiCommandProperty == "RunProtocolMatrixCommand");
    Assert(protocolMatrixAction.CliRoute.Contains("connectivity-probe protocol-matrix", StringComparison.Ordinal),
        "protocol matrix action must advertise the protocol-matrix CLI route");
    Assert(protocolMatrixAction.CliRoute.Contains("--latest-artifact-dir", StringComparison.Ordinal),
        "protocol matrix action must advertise latest artifact directory selection");
    Assert(protocolMatrixAction.CliRoute.Contains("--latest-probe-id", StringComparison.Ordinal),
        "protocol matrix action must advertise latest probe-id selection");
    Assert(protocolMatrixAction.CliRoute.Contains("connectivity-probe run --mode fixture --probe-id QCL-020", StringComparison.Ordinal),
        "protocol matrix action must advertise generated QCL-020 topology fixture evidence");
    Assert(protocolMatrixAction.CliRoute.Contains("qcl-020-wifi-adb-session-pass", StringComparison.Ordinal),
        "protocol matrix action must advertise QCL-020 fixture profile");
    Assert(protocolMatrixAction.CliRoute.Contains("connectivity-probe run --mode fixture --probe-id QCL-030", StringComparison.Ordinal),
        "protocol matrix action must advertise generated QCL-030 topology fixture evidence");
    Assert(protocolMatrixAction.CliRoute.Contains("qcl-030-local-only-hotspot-started", StringComparison.Ordinal),
        "protocol matrix action must advertise QCL-030 fixture profile");
    Assert(protocolMatrixAction.CliRoute.Contains("connectivity-probe run --mode fixture --probe-id QCL-040", StringComparison.Ordinal),
        "protocol matrix action must advertise generated QCL-040 topology fixture evidence");
    Assert(protocolMatrixAction.CliRoute.Contains("qcl-040-wifi-direct-phone-peer-pass", StringComparison.Ordinal),
        "protocol matrix action must advertise QCL-040 fixture profile");
    Assert(protocolMatrixAction.CliRoute.Contains("connectivity-probe run --mode fixture --probe-id QCL-041", StringComparison.Ordinal),
        "protocol matrix action must advertise generated QCL-041 topology fixture evidence");
    Assert(protocolMatrixAction.CliRoute.Contains("qcl-041-wifi-direct-windows-peer-pass", StringComparison.Ordinal),
        "protocol matrix action must advertise QCL-041 fixture profile");
    Assert(protocolMatrixAction.CliRoute.Contains("connectivity-probe run --mode live --probe-id QCL-040", StringComparison.Ordinal),
        "protocol matrix action must advertise live QCL-040 Wi-Fi Direct preflight");
    Assert(protocolMatrixAction.CliRoute.Contains("connectivity-probe run --mode live --probe-id QCL-041", StringComparison.Ordinal),
        "protocol matrix action must advertise live QCL-041 Wi-Fi Direct preflight");
    Assert(protocolMatrixAction.CliRoute.Contains("--adb $Adb --serial $QuestSerial", StringComparison.Ordinal),
        "protocol matrix action must use PowerShell variables for serial-scoped ADB placeholders");
    Assert(protocolMatrixAction.CliRoute.Contains("connectivity-probe wifi-direct-lifecycle-plan --probe-id QCL-040 --out $Qcl040LifecyclePlan --adb $Adb --serial $QuestSerial", StringComparison.Ordinal),
        "protocol matrix action must advertise the QCL-040 Wi-Fi Direct lifecycle execution plan route");
    Assert(protocolMatrixAction.CliRoute.Contains("connectivity-probe wifi-direct-lifecycle-plan --probe-id QCL-041 --out $Qcl041LifecyclePlan --adb $Adb --serial $QuestSerial", StringComparison.Ordinal),
        "protocol matrix action must advertise the QCL-041 Wi-Fi Direct lifecycle execution plan route");
    Assert(protocolMatrixAction.CliRoute.Contains("connectivity-probe wifi-direct-lifecycle-template --probe-id QCL-040 --out $Qcl040LifecycleTemplate", StringComparison.Ordinal),
        "protocol matrix action must advertise the QCL-040 Wi-Fi Direct lifecycle source template route");
    Assert(protocolMatrixAction.CliRoute.Contains("connectivity-probe wifi-direct-lifecycle-template --probe-id QCL-041 --out $Qcl041LifecycleTemplate", StringComparison.Ordinal),
        "protocol matrix action must advertise the QCL-041 Wi-Fi Direct lifecycle source template route");
    Assert(protocolMatrixAction.CliRoute.Contains("connectivity-probe run --mode fixture --probe-id QCL-040 --wifi-direct-lifecycle-report $LifecycleReport", StringComparison.Ordinal),
        "protocol matrix action must advertise the QCL-040 Wi-Fi Direct lifecycle normalization route");
    Assert(protocolMatrixAction.CliRoute.Contains("connectivity-probe run --mode fixture --probe-id QCL-041 --wifi-direct-lifecycle-report $LifecycleReport", StringComparison.Ordinal),
        "protocol matrix action must advertise the QCL-041 Wi-Fi Direct lifecycle normalization route");
    Assert(protocolMatrixAction.CliRoute.Contains("--input $TopologyFixtureReports", StringComparison.Ordinal),
        "protocol matrix action must advertise explicit topology fixture report inputs through a PowerShell variable");
    Assert(protocolMatrixAction.CliRoute.Contains("QCL-000", StringComparison.Ordinal),
        "protocol matrix action must include WebSocket command route evidence QCL-000");
    Assert(protocolMatrixAction.CliRoute.Contains("QCL-010", StringComparison.Ordinal),
        "protocol matrix action must include same-Wi-Fi TCP topology probe QCL-010");
    Assert(protocolMatrixAction.CliRoute.Contains("QCL-011", StringComparison.Ordinal),
        "protocol matrix action must include PC-hotspot TCP topology probe QCL-011");
    Assert(protocolMatrixAction.CliRoute.Contains("QCL-020", StringComparison.Ordinal),
        "protocol matrix action must include Wi-Fi ADB topology probe QCL-020");
    Assert(protocolMatrixAction.CliRoute.Contains("QCL-030", StringComparison.Ordinal),
        "protocol matrix action must include LocalOnlyHotspot topology probe QCL-030");
    Assert(protocolMatrixAction.CliRoute.Contains("QCL-040", StringComparison.Ordinal),
        "protocol matrix action must include phone-peer Wi-Fi Direct topology probe QCL-040");
    Assert(protocolMatrixAction.CliRoute.Contains("QCL-041", StringComparison.Ordinal),
        "protocol matrix action must include Windows-peer Wi-Fi Direct topology probe QCL-041");
    Assert(protocolMatrixAction.CliRoute.Contains("QCL-050", StringComparison.Ordinal),
        "protocol matrix action must include Bluetooth readiness probe QCL-050");
    Assert(protocolMatrixAction.CliRoute.Contains("QCL-051", StringComparison.Ordinal),
        "protocol matrix action must include Bluetooth reconnect probe QCL-051");
    Assert(protocolMatrixAction.CliRoute.Contains("QCL-080", StringComparison.Ordinal),
        "protocol matrix action must include UDP freshness probe QCL-080");
    Assert(protocolMatrixAction.CliRoute.Contains("QCL-081", StringComparison.Ordinal),
        "protocol matrix action must include LSL probe QCL-081");
    Assert(protocolMatrixAction.CliRoute.Contains("QCL-082", StringComparison.Ordinal),
        "protocol matrix action must include media-stream probe QCL-082");
    Assert(protocolMatrixAction.CliRoute.Contains("QCL-083", StringComparison.Ordinal),
        "protocol matrix action must include OSC probe QCL-083");
    Assert(protocolMatrixAction.CliRoute.Contains("QCL-084", StringComparison.Ordinal),
        "protocol matrix action must include ZeroMQ probe QCL-084");
    Assert(protocolMatrixAction.CliRoute.Contains("QCL-079", StringComparison.Ordinal),
        "protocol matrix action must include generic WebSocket probe QCL-079");
    Assert(protocolMatrixAction.CliRoute.Contains("--websocket-source", StringComparison.Ordinal),
        "protocol matrix action must advertise the QCL-079 generic WebSocket probe route");
    Assert(protocolMatrixAction.CliRoute.Contains("--websocket-route-descriptor", StringComparison.Ordinal),
        "protocol matrix action must advertise the QCL-079 Manifold WebSocket route descriptor input");
    Assert(protocolMatrixAction.CliRoute.Contains("--websocket-route-evidence", StringComparison.Ordinal),
        "protocol matrix action must advertise the QCL-079 Manifold WebSocket route evidence input");
    Assert(protocolMatrixAction.CliRoute.Contains("--media-stream-session-plan", StringComparison.Ordinal),
        "protocol matrix action must advertise the QCL-082 media-stream source-contract input");
    Assert(protocolMatrixAction.CliRoute.Contains("qcl082-product-media-plan", StringComparison.Ordinal),
        "protocol matrix action must advertise the QCL-082 product-media direct-Wi-Fi plan route");
    Assert(protocolMatrixAction.CliRoute.Contains("qcl082-product-media-direct-wifi-plan.json", StringComparison.Ordinal),
        "protocol matrix action must name the QCL-082 product-media plan artifact");
    Assert(protocolMatrixAction.CliRoute.Contains("direct-wifi-product-media-plan --out $DirectWifiProductMediaPlan", StringComparison.Ordinal),
        "protocol matrix action must advertise the combined direct-Wi-Fi product-media acceptance plan route");
    Assert(protocolMatrixAction.CliRoute.Contains("direct-wifi-product-media-acceptance-plan.json", StringComparison.Ordinal),
        "protocol matrix action must name the combined direct-Wi-Fi product-media acceptance plan artifact");
    Assert(protocolMatrixAction.CliRoute.Contains("--qcl082-report target\\connectivity-probe\\qcl082-rmanvid1-receiver-capture.json", StringComparison.Ordinal),
        "protocol matrix action must pass QCL-082 product-media evidence into the combined acceptance plan");
    Assert(protocolMatrixAction.CliRoute.Contains("emit-bridge-command-request", StringComparison.Ordinal),
        "protocol matrix action must advertise the QCL-082 bridge-command request generator");
    Assert(protocolMatrixAction.CliRoute.Contains("--bridge-command command.media_stream.start_source", StringComparison.Ordinal),
        "protocol matrix action must generate the QCL-082 start_source request through Hostess CLI");
    Assert(protocolMatrixAction.CliRoute.Contains("run-bridge-command-live-android", StringComparison.Ordinal),
        "protocol matrix action must advertise the QCL-082 live Android start_source command route");
    Assert(protocolMatrixAction.CliRoute.Contains("--execution-out $RuntimeStatus", StringComparison.Ordinal),
        "protocol matrix action must use the live Android execution artifact as the runtime-status source");
    Assert(protocolMatrixAction.CliRoute.Contains("media-stream-start-source.live-android-execution.json", StringComparison.Ordinal),
        "protocol matrix action must name the QCL-082 live Android execution sidecar");
    Assert(protocolMatrixAction.CliRoute.Contains("--media-stream-runtime-status", StringComparison.Ordinal),
        "protocol matrix action must advertise the QCL-082 broker runtime-status input");
    Assert(protocolMatrixAction.CliRoute.Contains("rmanvid1-receiver-capture", StringComparison.Ordinal),
        "protocol matrix action must advertise the QCL-082 RMANVID1 receiver capture route");
    Assert(protocolMatrixAction.CliRoute.Contains("--media-stream-rmanvid1-capture", StringComparison.Ordinal),
        "protocol matrix action must advertise the QCL-082 RMANVID1 capture evidence input");
    Assert(protocolMatrixAction.CliRoute.Contains("--media-stream-receiver-sidecar", StringComparison.Ordinal),
        "protocol matrix action must advertise the QCL-082 receiver sidecar evidence input");
    Assert(protocolMatrixAction.CliRoute.Contains("--topology-report", StringComparison.Ordinal),
        "protocol matrix action must advertise the QCL-082 receiver topology report input");
    Assert(protocolMatrixAction.CliRoute.Contains("--media-stream-topology-report", StringComparison.Ordinal),
        "protocol matrix action must advertise the QCL-082 follow-on topology report input");
    Assert(protocolMatrixAction.CliRoute.Contains("windows-firewall-rule --action verify --rule-profile qcl-082-rmanvid1-media", StringComparison.Ordinal),
        "protocol matrix action must advertise the product TCP firewall verification route");
    Assert(protocolMatrixAction.CliRoute.Contains("--rule-profile qcl-082-rmanvid1-media", StringComparison.Ordinal),
        "protocol matrix action must use the QCL-082 product media listener firewall profile");
    Assert(protocolMatrixAction.CliRoute.Contains("--firewall-report", StringComparison.Ordinal),
        "protocol matrix action must advertise the QCL-082 receiver firewall report input");
    Assert(protocolMatrixAction.CliRoute.Contains("--media-stream-firewall-report", StringComparison.Ordinal),
        "protocol matrix action must advertise the QCL-082 follow-on firewall report input");
    Assert(protocolMatrixAction.CliRoute.Contains("--latest-device-link-dir", StringComparison.Ordinal),
        "protocol matrix action must advertise latest device-link directory selection");
    Assert(protocolMatrixAction.CliRoute.Contains("--latest-stream-capability-dir", StringComparison.Ordinal),
        "protocol matrix action must advertise latest stream-capability directory selection");
    Assert(protocolMatrixAction.CliRoute.Contains("--latest-stream-probe-id", StringComparison.Ordinal),
        "protocol matrix action must advertise latest stream probe-id selection");
    Assert(protocolMatrixAction.CliRoute.Contains("companion-report projection", StringComparison.Ordinal),
        "protocol matrix action must render a companion-report projection");
    Assert(protocolMatrixAction.CliRoute.Contains("--include-protocol-matrix-inputs", StringComparison.Ordinal),
        "protocol matrix action must include protocol-matrix inputs in the report projection");
    Assert(protocolMatrixAction.CliRoute.Contains("companion-report transport-gates", StringComparison.Ordinal),
        "protocol matrix action must render the transport gate status artifact");
    Assert(protocolMatrixAction.CliRoute.Contains("--fail-on-pending", StringComparison.Ordinal),
        "protocol matrix action must advertise the pending transport gate automation switch");
    Assert(protocolMatrixAction.EvidenceArtifact.Contains("rusty.quest.connectivity_topology_probe.v1", StringComparison.Ordinal),
        "protocol matrix action must advertise topology probe evidence");
    Assert(protocolMatrixAction.EvidenceArtifact.Contains("rusty.hostess.direct_wifi_product_media_acceptance_plan.v1", StringComparison.Ordinal),
        "protocol matrix action must advertise direct-Wi-Fi product-media acceptance plan evidence");
    Assert(protocolMatrixAction.EvidenceArtifact.Contains("rusty.hostess.companion.report_projection.v1", StringComparison.Ordinal),
        "protocol matrix action must render the shared companion-report projection artifact");
    Assert(protocolMatrixAction.EvidenceArtifact.Contains("rusty.hostess.companion.transport_gate_report.v1", StringComparison.Ordinal),
        "protocol matrix action must advertise the transport gate status artifact");
    var firewallActions = OperatorActionCatalog.All
        .Where(action => action.ActionId.StartsWith("wpf.connectivity.firewall.", StringComparison.Ordinal))
        .ToArray();
    Assert(firewallActions.Length == 4,
        "firewall controls must expose plan/apply/verify/remove operator action descriptors");
    Assert(firewallActions.All(action =>
            action.CliRoute.Contains("connectivity-probe windows-firewall-rule --action ", StringComparison.Ordinal)),
        "firewall controls must stay backed by the windows-firewall-rule CLI route");
    Assert(firewallActions.All(action =>
            action.CliRoute.Contains("--rule-profile", StringComparison.Ordinal)),
        "firewall controls must advertise the CLI rule profile route");
    Assert(firewallActions.Any(action =>
            action.CliRoute.Contains("--handoff-script-out $AdminHandoffScript", StringComparison.Ordinal)
            && action.CliRoute.Contains("--handoff-verify-out $VerifyReport", StringComparison.Ordinal)),
        "firewall mutation controls must advertise PowerShell-variable handoff outputs");
    Assert(firewallActions.All(action =>
            action.EvidenceArtifact == "rusty.quest.connectivity_windows_firewall_rule.v1"),
        "firewall controls must advertise the emitted windows firewall evidence schema");
}

static ConnectivityProtocolEvidenceRow PromotedProtocolRow(
    string capabilityId,
    string probeId,
    string transportKind,
    string evidenceTier) =>
    new()
    {
        CapabilityId = capabilityId,
        ProbeId = probeId,
        TransportKind = transportKind,
        SemanticFamily = "generic_data_protocol",
        AuthorityOwner = evidenceTier == "quest_runtime"
            ? "rusty.quest.device_link"
            : "rusty.manifold.transport",
        RequiredForFoldIn = true,
        Status = "usable",
        PromotionState = "promoted",
        PromotionAllowed = true,
        EvidenceTier = evidenceTier,
        PromotionGate = "Quest-runtime or broker-owned evidence required",
        MissingGates = [],
        GateResults =
        [
            new ConnectivityProtocolEvidenceGate
            {
                GateId = $"gate.{probeId.ToLowerInvariant().Replace("-", string.Empty)}.promotion_allowed",
                Status = "satisfied",
                Evidence = "promotion.allowed=True",
            },
        ],
        Measurements = JsonSerializer.SerializeToElement(new { packets = 16 }),
    };

static void AssertArgument(IReadOnlyList<string> arguments, string name, string value)
{
    var index = arguments.ToList().IndexOf(name);
    Assert(index >= 0, $"missing argument {name}");
    Assert(index + 1 < arguments.Count, $"missing value for {name}");
    Assert(arguments[index + 1] == value, $"expected {name} {value}, got {arguments[index + 1]}");
}

static void PageViewModelsOwnWpfRowsAndSelections()
{
    AssertPageProperty("ReadinessPage", typeof(ReadinessPageViewModel));
    AssertPageProperty("DevicesPage", typeof(DevicesPageViewModel));
    AssertPageProperty("ConnectivityPage", typeof(ConnectivityPageViewModel));
    AssertPageProperty("SessionPage", typeof(SessionPageViewModel));
    AssertPageProperty("TransportsPage", typeof(TransportsPageViewModel));
    AssertPageProperty("CommandsPage", typeof(CommandsPageViewModel));
    AssertPageProperty("EvidencePage", typeof(EvidencePageViewModel));
    AssertPageProperty("WorkspacesPage", typeof(WorkspacesPageViewModel));

    var staleMainWindowFields = new HashSet<string>(StringComparer.Ordinal)
    {
        "selectedCheck",
        "selectedDeviceCheck",
        "selectedConnectivityCheck",
        "selectedSessionHistoryEntry",
        "selectedSessionPhase",
        "selectedSessionArtifact",
        "selectedTransport",
        "selectedCommandStage",
        "selectedEvidenceArtifact",
        "selectedWorkspace",
    };
    var mainWindowFields = typeof(MainWindowViewModel)
        .GetFields(BindingFlags.NonPublic | BindingFlags.Instance)
        .Select(field => field.Name);
    Assert(!mainWindowFields.Any(staleMainWindowFields.Contains),
        "page row selections must be owned by page viewmodels, not MainWindowViewModel fields");

    var vm = new MainWindowViewModel(
        new HostessctlReadinessService(),
        new HostessctlCatalogService(),
        new HostessctlCommandService(),
        new HostessctlSessionService(),
        new HostessctlConnectivityService());
    Assert(ReferenceEquals(vm.Checks, vm.ReadinessPage.Rows), "readiness rows must be page-owned");
    Assert(ReferenceEquals(vm.DeviceChecks, vm.DevicesPage.Rows), "device rows must be page-owned");
    Assert(ReferenceEquals(vm.ConnectivityChecks, vm.ConnectivityPage.Rows), "connectivity rows must be page-owned");
    Assert(ReferenceEquals(vm.SessionHistory, vm.SessionPage.History), "session history must be page-owned");
    Assert(ReferenceEquals(vm.SessionPhases, vm.SessionPage.Phases), "session phases must be page-owned");
    Assert(ReferenceEquals(vm.SessionArtifacts, vm.SessionPage.Artifacts), "session artifacts must be page-owned");
    Assert(ReferenceEquals(vm.Transports, vm.TransportsPage.Rows), "transport rows must be page-owned");
    Assert(ReferenceEquals(vm.CommandStages, vm.CommandsPage.Rows), "command rows must be page-owned");
    Assert(ReferenceEquals(vm.EvidenceArtifacts, vm.EvidencePage.Rows), "evidence rows must be page-owned");
    Assert(ReferenceEquals(vm.Workspaces, vm.WorkspacesPage.Rows), "workspace rows must be page-owned");

    var connectivityRow = new ConnectivityCheckViewModel(new ConnectivityCheck
    {
        Name = "qcl080.product_rule_verified",
        Status = "pass",
        Evidence = "target/qcl080.json",
        Notes = "product-owned firewall rule verified",
        Observed = JsonSerializer.SerializeToElement(new { product_rule_verified = true }),
    });
    vm.ConnectivityChecks.Add(connectivityRow);
    vm.SelectedNavigationItem = vm.NavigationItems.Single(item => item.Key == "connectivity");
    vm.SelectedConnectivityCheck = connectivityRow;

    Assert(ReferenceEquals(vm.ConnectivityPage.SelectedRow, connectivityRow),
        "facade selection must write through to the connectivity page");
    Assert(vm.SelectedDetailTitle == "qcl080.product_rule_verified",
        "detail panel must project the selected page row title");
    Assert(vm.SelectedDetailText.Contains("product-owned firewall rule verified", StringComparison.Ordinal),
        "detail panel must project the selected page row detail text");

    var workspaceRow = new WorkspaceViewModel(
        new CompanionWorkspaceDescriptor
        {
            WorkspaceId = "workspace.fixture",
            Title = "Fixture workspace",
            SupportedFrontends = ["wpf"],
            Modules = [new WorkspaceModuleSelection { ModuleId = "module.fixture", Required = true, Prominent = true }],
        },
        new Dictionary<string, CompanionModuleDescriptor>(StringComparer.OrdinalIgnoreCase)
        {
            ["module.fixture"] = new CompanionModuleDescriptor { ModuleId = "module.fixture", Title = "Fixture module" },
        });
    vm.Workspaces.Add(workspaceRow);
    vm.SelectedNavigationItem = vm.NavigationItems.Single(item => item.Key == "workspaces");
    vm.SelectedWorkspace = workspaceRow;

    Assert(ReferenceEquals(vm.WorkspacesPage.SelectedRow, workspaceRow),
        "facade workspace selection must write through to the workspaces page");
    Assert(vm.SelectedDetailTitle == "Fixture workspace",
        "detail panel must project the selected workspace title");
    Assert(vm.SelectedDetailText.Contains("module.fixture", StringComparison.Ordinal),
        "detail panel must project selected workspace module composition");
}

static void PageViewModelsProjectBackendReports()
{
    var readinessReport = new ReadinessReport
    {
        Status = "warn",
        Checks =
        [
            new ReadinessCheck
            {
                CheckId = "device.adb",
                Group = "device",
                Title = "ADB device",
                Status = "pass",
                Severity = "info",
                Evidence = "serial=device",
                Observed = JsonSerializer.SerializeToElement(new { serial = "fixture" }),
            },
            new ReadinessCheck
            {
                CheckId = "host.python",
                Group = "host",
                Title = "Python",
                Status = "pass",
                Severity = "info",
                Evidence = "python.exe",
                Observed = JsonSerializer.SerializeToElement(new { path = "python.exe" }),
            },
        ],
    };

    var readinessPage = new ReadinessPageViewModel();
    readinessPage.ApplyReport(readinessReport);
    Assert(readinessPage.Rows.Count == 2, "readiness page must project all readiness checks");
    Assert(readinessPage.SelectedRow?.CheckId == "device.adb", "readiness page must select the first projected row");

    var devicesPage = new DevicesPageViewModel();
    devicesPage.ApplyReadiness(readinessReport);
    Assert(devicesPage.Rows.Count == 1 && devicesPage.Rows[0].CheckId == "device.adb",
        "devices page must project only device/runtime/network readiness groups");

    var deviceLinkReport = ReadFixture<DeviceLinkReport>("device-link-pass.json");
    devicesPage.ApplyDeviceLink(deviceLinkReport);
    Assert(devicesPage.Rows.Any(row => row.CheckId == "device_link.identity"),
        "devices page must project device-link identity rows");

    var transportsPage = new TransportsPageViewModel();
    transportsPage.ApplyDeviceLink(deviceLinkReport);
    Assert(transportsPage.Rows.Any(row => row.TransportId == "capability.command.hostess_makepad_bridge"),
        "transports page must project device-link stream capabilities");

    var connectivityPage = new ConnectivityPageViewModel();
    connectivityPage.ApplyRows(
    [
        new ConnectivityCheck
        {
            Name = "qcl080.product_rule_verified",
            Status = "pass",
            Evidence = "target/qcl080.json",
            Notes = "product-owned firewall rule verified",
            Observed = JsonSerializer.SerializeToElement(new { product_rule_verified = true }),
        },
    ]);
    Assert(connectivityPage.SelectedRow?.Name == "qcl080.product_rule_verified",
        "connectivity page must select the first projected row");

    var commandsPage = new CommandsPageViewModel();
    commandsPage.ApplyExecution(new BridgeCommandExecution
    {
        StageObservations =
        [
            new CommandStageObservation
            {
                Stage = "applied",
                Status = "pass",
                EvidenceRefs = ["target/command.json"],
            },
        ],
        Issues =
        [
            new CommandIssue
            {
                IssueCode = "hostess.issue.fixture",
                Message = "fixture issue",
            },
        ],
    });
    Assert(commandsPage.Rows.Any(row => row.Stage == "applied" && row.Status == "pass"),
        "commands page must project command stages");
    Assert(commandsPage.Rows.Any(row => row.Stage == "hostess.issue.fixture" && row.Status == "fail"),
        "commands page must project command issues as failure rows");

    var catalog = new CompanionCatalog
    {
        Modules =
        [
            new CompanionModuleDescriptor
            {
                ModuleId = "module.fixture",
                Title = "Fixture module",
                OwnerLane = "hostess",
                EvidenceArtifacts =
                [
                    new EvidenceArtifactBinding
                    {
                        Id = "artifact.fixture",
                        Schema = "rusty.fixture.v1",
                        OwnerLane = "hostess",
                    },
                ],
            },
        ],
        Workspaces =
        [
            new CompanionWorkspaceDescriptor
            {
                WorkspaceId = "workspace.fixture",
                Title = "Fixture workspace",
                SupportedFrontends = ["wpf"],
                Modules =
                [
                    new WorkspaceModuleSelection
                    {
                        ModuleId = "module.fixture",
                        Required = true,
                        Prominent = true,
                    },
                    new WorkspaceModuleSelection
                    {
                        ModuleId = "module.background",
                        Required = false,
                        Prominent = false,
                    },
                ],
                Sensitivity = ["private"],
                SourcePath = "descriptors/workspaces/fixture.json",
            },
        ],
        Issues =
        [
            new CatalogIssue
            {
                Severity = "error",
                Code = "hostess.issue.companion_catalog.workspace_unknown_module",
                Message = "workspace workspace.fixture references unknown module module.background",
                WorkspaceId = "workspace.fixture",
                ModuleId = "module.background",
            },
        ],
    };

    var evidencePage = new EvidencePageViewModel();
    evidencePage.ApplyCatalog(catalog);
    Assert(evidencePage.Rows.Single().ArtifactId == "artifact.fixture",
        "evidence page must project module evidence artifact bindings");

    var workspacesPage = new WorkspacesPageViewModel();
    workspacesPage.ApplyCatalog(catalog);
    var workspace = workspacesPage.Rows.Single();
    Assert(workspace.WorkspaceId == "workspace.fixture", "workspaces page must project catalog workspace descriptors");
    Assert(workspace.RequiredCount == 1 && workspace.OptionalCount == 1,
        "workspace row must preserve required and optional module counts");
    Assert(workspace.ModuleSummary.Contains("module.fixture (Fixture module)", StringComparison.Ordinal),
        "workspace detail must resolve known module titles from the catalog");
    Assert(workspace.ModuleSummary.Contains("module.background (unresolved descriptor)", StringComparison.Ordinal),
        "workspace detail must keep unresolved module ids visible instead of inventing module semantics");
    Assert(workspace.ValidationStatus == "fail" && workspace.IssueCount == 1,
        "workspace row must project catalog-emitted validation issues");
    Assert(workspace.DetailText.Contains("workspace_unknown_module", StringComparison.Ordinal),
        "workspace detail must render the catalog issue code for operator inspection");

    var sessionPage = new SessionPageViewModel();
    sessionPage.ApplySession(
        new CompanionSessionReport
        {
            SessionId = "session-a",
            Status = "pass",
            Phases =
            [
                new SessionPhase
                {
                    PhaseId = "phase-a",
                    Title = "Phase A",
                    Status = "pass",
                    Summary = new SessionSummary { ActionCount = 1 },
                    ArtifactRefs = ["artifact-a"],
                },
            ],
            ArtifactRefs =
            [
                new SessionArtifactRef
                {
                    ArtifactId = "artifact-a",
                    Role = "device_link_report",
                    Path = "target/artifact-a.json",
                    Schema = "rusty.quest.device_link.v1",
                    ValidationStatus = "pass",
                },
            ],
        },
        artifact => $"preview {artifact.ArtifactId}");
    Assert(sessionPage.SelectedPhase?.PhaseId == "phase-a", "session page must select first phase");
    Assert(sessionPage.Artifacts.Single().ArtifactId == "artifact-a",
        "session page must expand artifacts for selected phase");
    Assert(sessionPage.SelectedDetailText.Contains("Phase: phase-a", StringComparison.Ordinal),
        "session detail must project selected phase before an artifact is selected");
    sessionPage.SelectedArtifact = sessionPage.Artifacts.Single();
    Assert(sessionPage.SelectedDetailText.Contains("preview artifact-a", StringComparison.Ordinal),
        "session detail must project selected artifact preview");

    sessionPage.ApplyHistory(
    [
        new CompanionSessionReport { SessionId = "session-a", ReportPath = "target/a.json" },
        new CompanionSessionReport { SessionId = "session-b", ReportPath = "target/b.json" },
    ],
        "target/b.json");
    Assert(sessionPage.SelectedHistoryEntry?.SessionId == "session-b",
        "session page must select requested history entry by report path");
}

static void AssertPageProperty(string propertyName, Type expectedType)
{
    var property = typeof(MainWindowViewModel).GetProperty(propertyName);
    Assert(property is not null, $"missing page property {propertyName}");
    Assert(property!.PropertyType == expectedType, $"{propertyName} must be {expectedType.Name}");
}

static T ReadFixture<T>(string name)
{
    var path = Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "Fixtures", name);
    using var stream = File.OpenRead(Path.GetFullPath(path));
    return JsonSerializer.Deserialize<T>(
            stream,
            new JsonSerializerOptions { PropertyNameCaseInsensitive = true })
        ?? throw new InvalidOperationException($"fixture {name} was empty");
}

static bool RustyQuestMediaStreamSessionPlanExists()
{
    var repoRoot = LocateHostessRepoRoot();
    var planPath = Path.GetFullPath(Path.Combine(
        repoRoot.FullName,
        "..",
        "rusty-quest",
        "fixtures",
        "media-stream-sessions",
        "display-composite-mediaprojection-h264.plan.json"));
    return File.Exists(planPath);
}

static bool ManifoldWebSocketStreamEvidenceExists()
{
    var repoRoot = LocateHostessRepoRoot();
    var routePath = Path.GetFullPath(Path.Combine(
        repoRoot.FullName,
        "..",
        "rusty-manifold",
        "fixtures",
        "bridge-route",
        "stream-websocket-ordered-route.json"));
    var evidencePath = Path.GetFullPath(Path.Combine(
        repoRoot.FullName,
        "..",
        "rusty-manifold",
        "fixtures",
        "bridge-route",
        "stream-websocket-ordered-evidence.json"));
    return File.Exists(routePath) && File.Exists(evidencePath);
}

static DirectoryInfo LocateHostessRepoRoot()
{
    var current = new DirectoryInfo(AppContext.BaseDirectory);
    while (current is not null)
    {
        if (File.Exists(Path.Combine(current.FullName, "tools", "hostessctl", "hostessctl.py")))
        {
            return current;
        }
        current = current.Parent;
    }
    throw new InvalidOperationException("Could not locate rusty-hostess repository root.");
}

static void Assert(bool condition, string message)
{
    if (!condition)
    {
        throw new InvalidOperationException(message);
    }
}
