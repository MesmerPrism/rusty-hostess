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
    public static void PageViewModelsOwnWpfRowsAndSelections()
    {
        AssertPageProperty("ReadinessPage", typeof(ReadinessPageViewModel));
        AssertPageProperty("DevicesPage", typeof(DevicesPageViewModel));
        AssertPageProperty("ConnectivityPage", typeof(ConnectivityPageViewModel));
        AssertPageProperty("SessionPage", typeof(SessionPageViewModel));
        AssertPageProperty("TransportsPage", typeof(TransportsPageViewModel));
        AssertPageProperty("CommandsPage", typeof(CommandsPageViewModel));
        AssertPageProperty("EvidencePage", typeof(EvidencePageViewModel));
        AssertPageProperty("WorkspacesPage", typeof(WorkspacesPageViewModel));
        AssertPageProperty("ProjectRunnerPage", typeof(ProjectRunnerPageViewModel));
    
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
            "selectedProjectRunnerRow",
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
        Assert(ReferenceEquals(vm.ProjectRunnerRows, vm.ProjectRunnerPage.Rows),
            "project-runner rows must be page-owned");
    
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

        var projectRunnerProjection = new ProjectRunnerProjection
        {
            GenerationId = "generation.fixture",
            RunId = "run.fixture",
            CompletionMarker = "target/project-runner/fixture.complete.json",
            Rows =
            [
                new ProjectRunnerProjectionRow
                {
                    RowId = "closure",
                    Kind = "closure",
                    Title = "Exact closure",
                    Status = "pass",
                    Owner = "rusty.hostess",
                    Detail = "lock and project match",
                },
            ],
        };
        vm.ProjectRunnerPage.ApplyProjection(projectRunnerProjection);
        vm.SelectedNavigationItem = vm.NavigationItems.Single(item => item.Key == "project-runner");
        vm.SelectedProjectRunnerRow = vm.ProjectRunnerRows.Single();
        Assert(vm.IsProjectRunnerSelected, "project runner must have a dedicated navigation surface");
        Assert(vm.SelectedDetailText.Contains("fixture.complete.json", StringComparison.Ordinal),
            "project-runner details must preserve the completion-marker source");
    }
    

    public static void PageViewModelsProjectBackendReports()
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
    

}
