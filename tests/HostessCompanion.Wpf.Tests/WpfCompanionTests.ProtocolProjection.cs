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
    public static void ProtocolMatrixRowsExposePromotionGates()
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
    

    public static void ProtocolMatrixRowsExposeLatestPromotedEvidence()
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
    

    public static void CompanionReportProjectionRowsExposeSharedArtifact()
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
    

    public static void CompanionReportProjectionProjectsTopologyProbeRows()
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
    

    public static void CompanionReportProjectionRowsExposeTransportCoverage()
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
    

}
