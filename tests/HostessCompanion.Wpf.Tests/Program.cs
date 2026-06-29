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
    ("connectivity service builds companion report projection artifact", ConnectivityServiceBuildsCompanionReportProjectionArtifact),
    ("firewall rows expose product verification", FirewallRowsExposeProductVerification),
    ("firewall default names stay product scoped", FirewallDefaultNamesStayProductScoped),
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
    Assert(run.Projection.Schema == "rusty.hostess.companion.report_projection.v1",
        "service must return the companion-report projection schema");
    Assert(run.Projection.Rows.Any(row => row.RowId == "protocol_matrix.summary"),
        "projection must include the protocol matrix summary row");
    Assert(run.Projection.SourceArtifacts.Any(source => source.Role == "connectivity_suite_run"),
        "projection must include the suite source artifact");
    Assert(run.Projection.SourceArtifacts.Any(source => source.Role == "connectivity_probe_report"),
        "projection must include protocol-matrix source probe artifacts");
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

    vm.ConnectivityPort = "19000";
    Assert(vm.ConnectivityRuleName == "Rusty Hostess WPF QCL-080 UDP Freshness 19000",
        "UDP port changes must preserve WPF product-scoped rule name");

    vm.ConnectivityProtocol = "TCP";
    Assert(vm.ConnectivityRuleName == "Rusty Hostess WPF QCL-010 TCP Echo 19000",
        "protocol changes must preserve WPF product-scoped rule name");

    vm.ConnectivityPort = "18766";
    Assert(vm.ConnectivityRuleName == "Rusty Hostess WPF QCL-010 TCP Echo 18766",
        "TCP port changes must preserve WPF product-scoped rule name");
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
    Assert(
        OperatorActionCatalog.All.Any(action =>
            action.UiCommandProperty == "RunProtocolMatrixCommand"
            && action.CliRoute.Contains("connectivity-probe protocol-matrix", StringComparison.Ordinal)
            && action.CliRoute.Contains("--latest-artifact-dir", StringComparison.Ordinal)
            && action.CliRoute.Contains("--latest-probe-id", StringComparison.Ordinal)
            && action.CliRoute.Contains("QCL-050", StringComparison.Ordinal)
            && action.CliRoute.Contains("QCL-051", StringComparison.Ordinal)
            && action.CliRoute.Contains("--latest-device-link-dir", StringComparison.Ordinal)
            && action.CliRoute.Contains("--latest-stream-capability-dir", StringComparison.Ordinal)
            && action.CliRoute.Contains("--latest-stream-probe-id", StringComparison.Ordinal)
            && action.CliRoute.Contains("companion-report projection", StringComparison.Ordinal)
            && action.CliRoute.Contains("--connectivity-probe", StringComparison.Ordinal)
            && action.EvidenceArtifact.Contains("rusty.quest.connectivity_topology_probe.v1", StringComparison.Ordinal)
            && action.EvidenceArtifact.Contains("rusty.hostess.companion.report_projection.v1", StringComparison.Ordinal)),
        "protocol matrix must render the shared companion-report projection artifact");
    var firewallActions = OperatorActionCatalog.All
        .Where(action => action.ActionId.StartsWith("wpf.connectivity.firewall.", StringComparison.Ordinal))
        .ToArray();
    Assert(firewallActions.Length == 4,
        "firewall controls must expose plan/apply/verify/remove operator action descriptors");
    Assert(firewallActions.All(action =>
            action.CliRoute.StartsWith("connectivity-probe windows-firewall-rule --action ", StringComparison.Ordinal)),
        "firewall controls must stay backed by the windows-firewall-rule CLI route");
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

static void Assert(bool condition, string message)
{
    if (!condition)
    {
        throw new InvalidOperationException(message);
    }
}
