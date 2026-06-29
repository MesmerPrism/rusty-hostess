using System.Collections.ObjectModel;
using System.Windows.Media;
using HostessCompanion.Wpf.Models;
using HostessCompanion.Wpf.Services;

namespace HostessCompanion.Wpf.ViewModels;

public sealed partial class MainWindowViewModel : ObservableViewModel
{
    private readonly HostessctlReadinessService readinessService;
    private readonly HostessctlCatalogService catalogService;
    private readonly HostessctlCommandService commandService;
    private readonly HostessctlSessionService sessionService;
    private readonly HostessctlConnectivityService connectivityService;
    private bool isBusy;
    private string reportStatus = "not run";
    private string catalogStatus = "not loaded";
    private string connectivityStatus = "not checked";
    private string summaryLabel = "No companion reports loaded.";
    private string serial = "";
    private string connectivityProgram = HostessctlConnectivityService.DefaultProductProgramPath();
    private string connectivityProtocol = "UDP";
    private string connectivityPort = "18767";
    private string connectivityProfile = "Public";
    private string connectivityRemoteAddress = "LocalSubnet";
    private string connectivityRuleName = "Rusty Hostess WPF QCL-080 UDP Freshness 18767";
    private bool useQuestProfile = true;
    private bool checkBroker;
    private NavigationItemViewModel? selectedNavigationItem;
    private ConnectivityFirewallRuleReport? currentFirewallRuleReport;

    public MainWindowViewModel(
        HostessctlReadinessService readinessService,
        HostessctlCatalogService catalogService,
        HostessctlCommandService commandService,
        HostessctlSessionService sessionService,
        HostessctlConnectivityService connectivityService)
    {
        this.readinessService = readinessService;
        this.catalogService = catalogService;
        this.commandService = commandService;
        this.sessionService = sessionService;
        this.connectivityService = connectivityService;
        NavigationItems.Add(new NavigationItemViewModel("readiness", "Readiness"));
        NavigationItems.Add(new NavigationItemViewModel("session", "Session"));
        NavigationItems.Add(new NavigationItemViewModel("devices", "Devices"));
        NavigationItems.Add(new NavigationItemViewModel("connectivity", "Connectivity"));
        NavigationItems.Add(new NavigationItemViewModel("transports", "Transports"));
        NavigationItems.Add(new NavigationItemViewModel("commands", "Commands"));
        NavigationItems.Add(new NavigationItemViewModel("evidence", "Evidence"));
        NavigationItems.Add(new NavigationItemViewModel("workspaces", "Workspaces"));
        selectedNavigationItem = NavigationItems[0];
        ConnectDetailNotifications(ReadinessPage, nameof(SelectedCheck));
        ConnectDetailNotifications(DevicesPage, nameof(SelectedDeviceCheck));
        ConnectDetailNotifications(ConnectivityPage, nameof(SelectedConnectivityCheck));
        ConnectDetailNotifications(TransportsPage, nameof(SelectedTransport));
        ConnectDetailNotifications(CommandsPage, nameof(SelectedCommandStage));
        ConnectDetailNotifications(EvidencePage, nameof(SelectedEvidenceArtifact));
        ConnectDetailNotifications(WorkspacesPage, nameof(SelectedWorkspace));
        ConnectSessionNotifications();
        RefreshCommand = new AsyncRelayCommand(RefreshAsync, () => !IsBusy);
        RunSessionCommand = new AsyncRelayCommand(RunSessionAsync, () => !IsBusy);
        LoadSessionHistoryCommand = new AsyncRelayCommand(LoadSessionHistoryAsync, () => !IsBusy);
        LoadSelectedSessionCommand = new AsyncRelayCommand(
            LoadSelectedSessionAsync,
            () => !IsBusy && SelectedSessionHistoryEntry is not null);
        RunProbeCommand = new AsyncRelayCommand(RunProbeAsync, () => !IsBusy);
        PlanFirewallRuleCommand = new AsyncRelayCommand(PlanFirewallRuleAsync, () => !IsBusy);
        ApplyFirewallRuleCommand = new AsyncRelayCommand(ApplyFirewallRuleAsync, () => !IsBusy);
        VerifyFirewallRuleCommand = new AsyncRelayCommand(VerifyFirewallRuleAsync, () => !IsBusy);
        VerifyConnectivityCommand = new AsyncRelayCommand(VerifyConnectivityAsync, () => !IsBusy);
        RunConnectivitySuiteCommand = new AsyncRelayCommand(RunConnectivitySuiteAsync, () => !IsBusy);
        RunProtocolMatrixCommand = new AsyncRelayCommand(RunProtocolMatrixAsync, () => !IsBusy);
        RemoveFirewallRuleCommand = new AsyncRelayCommand(RemoveFirewallRuleAsync, () => !IsBusy);
    }

    public ObservableCollection<NavigationItemViewModel> NavigationItems { get; } = [];

    public ReadinessPageViewModel ReadinessPage { get; } = new();

    public DevicesPageViewModel DevicesPage { get; } = new();

    public ConnectivityPageViewModel ConnectivityPage { get; } = new();

    public SessionPageViewModel SessionPage { get; } = new();

    public TransportsPageViewModel TransportsPage { get; } = new();

    public CommandsPageViewModel CommandsPage { get; } = new();

    public EvidencePageViewModel EvidencePage { get; } = new();

    public WorkspacesPageViewModel WorkspacesPage { get; } = new();

    public ObservableCollection<CheckViewModel> Checks => ReadinessPage.Rows;

    public ObservableCollection<CheckViewModel> DeviceChecks => DevicesPage.Rows;

    public ObservableCollection<ConnectivityCheckViewModel> ConnectivityChecks => ConnectivityPage.Rows;

    public ObservableCollection<SessionHistoryEntryViewModel> SessionHistory => SessionPage.History;

    public ObservableCollection<SessionPhaseViewModel> SessionPhases => SessionPage.Phases;

    public ObservableCollection<SessionArtifactViewModel> SessionArtifacts => SessionPage.Artifacts;

    public ObservableCollection<TransportViewModel> Transports => TransportsPage.Rows;

    public ObservableCollection<CommandStageViewModel> CommandStages => CommandsPage.Rows;

    public ObservableCollection<EvidenceArtifactViewModel> EvidenceArtifacts => EvidencePage.Rows;

    public ObservableCollection<WorkspaceViewModel> Workspaces => WorkspacesPage.Rows;

    public IReadOnlyList<OperatorActionDescriptor> OperatorActions => OperatorActionCatalog.All;

    public AsyncRelayCommand RefreshCommand { get; }

    public AsyncRelayCommand RunSessionCommand { get; }

    public AsyncRelayCommand LoadSessionHistoryCommand { get; }

    public AsyncRelayCommand LoadSelectedSessionCommand { get; }

    public AsyncRelayCommand RunProbeCommand { get; }

    public AsyncRelayCommand PlanFirewallRuleCommand { get; }

    public AsyncRelayCommand ApplyFirewallRuleCommand { get; }

    public AsyncRelayCommand VerifyFirewallRuleCommand { get; }

    public AsyncRelayCommand VerifyConnectivityCommand { get; }

    public AsyncRelayCommand RunConnectivitySuiteCommand { get; }

    public AsyncRelayCommand RunProtocolMatrixCommand { get; }

    public AsyncRelayCommand RemoveFirewallRuleCommand { get; }

    public bool IsBusy
    {
        get => isBusy;
        private set
        {
            if (SetField(ref isBusy, value))
            {
                RefreshCommand.RaiseCanExecuteChanged();
                RunSessionCommand.RaiseCanExecuteChanged();
                LoadSessionHistoryCommand.RaiseCanExecuteChanged();
                LoadSelectedSessionCommand.RaiseCanExecuteChanged();
                RunProbeCommand.RaiseCanExecuteChanged();
                PlanFirewallRuleCommand.RaiseCanExecuteChanged();
                ApplyFirewallRuleCommand.RaiseCanExecuteChanged();
                VerifyFirewallRuleCommand.RaiseCanExecuteChanged();
                VerifyConnectivityCommand.RaiseCanExecuteChanged();
                RunConnectivitySuiteCommand.RaiseCanExecuteChanged();
                RunProtocolMatrixCommand.RaiseCanExecuteChanged();
                RemoveFirewallRuleCommand.RaiseCanExecuteChanged();
                OnPropertyChanged(nameof(RefreshButtonLabel));
                OnPropertyChanged(nameof(RunSessionButtonLabel));
                OnPropertyChanged(nameof(LoadSessionHistoryButtonLabel));
                OnPropertyChanged(nameof(LoadSelectedSessionButtonLabel));
                OnPropertyChanged(nameof(RunProbeButtonLabel));
                OnPropertyChanged(nameof(PlanFirewallRuleButtonLabel));
                OnPropertyChanged(nameof(ApplyFirewallRuleButtonLabel));
                OnPropertyChanged(nameof(VerifyFirewallRuleButtonLabel));
                OnPropertyChanged(nameof(VerifyConnectivityButtonLabel));
                OnPropertyChanged(nameof(RunConnectivitySuiteButtonLabel));
                OnPropertyChanged(nameof(RunProtocolMatrixButtonLabel));
                OnPropertyChanged(nameof(RemoveFirewallRuleButtonLabel));
            }
        }
    }

    public string RefreshButtonLabel => IsBusy ? "Refreshing" : "Refresh";

    public string RunSessionButtonLabel => IsBusy ? "Running" : "Run session";

    public string LoadSessionHistoryButtonLabel => IsBusy ? "Loading" : "History";

    public string LoadSelectedSessionButtonLabel => IsBusy ? "Loading" : "Load";

    public string RunProbeButtonLabel => IsBusy ? "Running" : "Run safe probe";

    public string PlanFirewallRuleButtonLabel => IsBusy ? "Planning" : "Plan rule";

    public string ApplyFirewallRuleButtonLabel => IsBusy ? "Applying" : "Apply rule";

    public string VerifyFirewallRuleButtonLabel => IsBusy ? "Verifying" : "Verify rule";

    public string VerifyConnectivityButtonLabel =>
        IsBusy ? "Verifying" : ConnectivityProtocol == "UDP" ? "Verify QCL-080" : "Verify QCL-010";

    public string RunConnectivitySuiteButtonLabel => IsBusy ? "Running" : "Run suite";

    public string RunProtocolMatrixButtonLabel => IsBusy ? "Building" : "Protocol matrix";

    public string RemoveFirewallRuleButtonLabel => IsBusy ? "Removing" : "Remove rule";

    public string Serial
    {
        get => serial;
        set => SetField(ref serial, value);
    }

    public bool UseQuestProfile
    {
        get => useQuestProfile;
        set => SetField(ref useQuestProfile, value);
    }

    public bool CheckBroker
    {
        get => checkBroker;
        set => SetField(ref checkBroker, value);
    }

    public string ConnectivityProgram
    {
        get => connectivityProgram;
        set => SetField(ref connectivityProgram, value);
    }

    public string ConnectivityProtocol
    {
        get => connectivityProtocol;
        set
        {
            var previousDefaultRuleName = DefaultConnectivityRuleName(connectivityPort, connectivityProtocol);
            var nextProtocol = NormalizeConnectivityProtocol(value);
            if (SetField(ref connectivityProtocol, nextProtocol))
            {
                if (string.IsNullOrWhiteSpace(ConnectivityRuleName)
                    || string.Equals(ConnectivityRuleName, previousDefaultRuleName, StringComparison.Ordinal))
                {
                    ConnectivityRuleName = DefaultConnectivityRuleName(connectivityPort, nextProtocol);
                }
                OnPropertyChanged(nameof(VerifyConnectivityButtonLabel));
            }
        }
    }

    public string ConnectivityPort
    {
        get => connectivityPort;
        set
        {
            var previousDefaultRuleName = DefaultConnectivityRuleName(connectivityPort, connectivityProtocol);
            if (SetField(ref connectivityPort, value)
                && (string.IsNullOrWhiteSpace(ConnectivityRuleName)
                    || string.Equals(ConnectivityRuleName, previousDefaultRuleName, StringComparison.Ordinal)))
            {
                ConnectivityRuleName = DefaultConnectivityRuleName(value, connectivityProtocol);
            }
        }
    }

    public string ConnectivityProfile
    {
        get => connectivityProfile;
        set => SetField(ref connectivityProfile, value);
    }

    public string ConnectivityRemoteAddress
    {
        get => connectivityRemoteAddress;
        set => SetField(ref connectivityRemoteAddress, value);
    }

    public string ConnectivityRuleName
    {
        get => connectivityRuleName;
        set => SetField(ref connectivityRuleName, value);
    }

    public NavigationItemViewModel? SelectedNavigationItem
    {
        get => selectedNavigationItem;
        set
        {
            if (SetField(ref selectedNavigationItem, value))
            {
                OnPropertyChanged(nameof(PageTitle));
                OnPropertyChanged(nameof(IsReadinessSelected));
                OnPropertyChanged(nameof(IsSessionSelected));
                OnPropertyChanged(nameof(IsDevicesSelected));
                OnPropertyChanged(nameof(IsConnectivitySelected));
                OnPropertyChanged(nameof(IsTransportsSelected));
                OnPropertyChanged(nameof(IsCommandsSelected));
                OnPropertyChanged(nameof(IsEvidenceSelected));
                OnPropertyChanged(nameof(IsWorkspacesSelected));
                OnDetailChanged();
            }
        }
    }

    public CheckViewModel? SelectedCheck
    {
        get => ReadinessPage.SelectedRow;
        set => ReadinessPage.SelectedRow = value;
    }

    public CheckViewModel? SelectedDeviceCheck
    {
        get => DevicesPage.SelectedRow;
        set => DevicesPage.SelectedRow = value;
    }

    public ConnectivityCheckViewModel? SelectedConnectivityCheck
    {
        get => ConnectivityPage.SelectedRow;
        set => ConnectivityPage.SelectedRow = value;
    }

    public SessionHistoryEntryViewModel? SelectedSessionHistoryEntry
    {
        get => SessionPage.SelectedHistoryEntry;
        set => SessionPage.SelectedHistoryEntry = value;
    }

    public SessionPhaseViewModel? SelectedSessionPhase
    {
        get => SessionPage.SelectedPhase;
        set => SessionPage.SelectedPhase = value;
    }

    public SessionArtifactViewModel? SelectedSessionArtifact
    {
        get => SessionPage.SelectedArtifact;
        set => SessionPage.SelectedArtifact = value;
    }

    public TransportViewModel? SelectedTransport
    {
        get => TransportsPage.SelectedRow;
        set => TransportsPage.SelectedRow = value;
    }

    public CommandStageViewModel? SelectedCommandStage
    {
        get => CommandsPage.SelectedRow;
        set => CommandsPage.SelectedRow = value;
    }

    public EvidenceArtifactViewModel? SelectedEvidenceArtifact
    {
        get => EvidencePage.SelectedRow;
        set => EvidencePage.SelectedRow = value;
    }

    public WorkspaceViewModel? SelectedWorkspace
    {
        get => WorkspacesPage.SelectedRow;
        set => WorkspacesPage.SelectedRow = value;
    }

    public string PageTitle => SelectedNavigationKey switch
    {
        "session" => "Session",
        "devices" => "Devices",
        "connectivity" => "Connectivity",
        "transports" => "Transports",
        "commands" => "Commands",
        "evidence" => "Evidence",
        "workspaces" => "Workspaces",
        _ => "Readiness",
    };

    public bool IsReadinessSelected => SelectedNavigationKey == "readiness";

    public bool IsSessionSelected => SelectedNavigationKey == "session";

    public bool IsDevicesSelected => SelectedNavigationKey == "devices";

    public bool IsConnectivitySelected => SelectedNavigationKey == "connectivity";

    public bool IsTransportsSelected => SelectedNavigationKey == "transports";

    public bool IsCommandsSelected => SelectedNavigationKey == "commands";

    public bool IsEvidenceSelected => SelectedNavigationKey == "evidence";

    public bool IsWorkspacesSelected => SelectedNavigationKey == "workspaces";

    public string ReportStatusLabel => $"Readiness: {reportStatus}";

    public Brush ReportStatusBrush => BrushForStatus(reportStatus);

    public string CatalogStatusLabel => $"Catalog: {catalogStatus}";

    public Brush CatalogStatusBrush => BrushForStatus(catalogStatus);

    public string ConnectivityStatusLabel => $"Connectivity: {connectivityStatus}";

    public Brush ConnectivityStatusBrush => BrushForStatus(connectivityStatus);

    public string SummaryLabel
    {
        get => summaryLabel;
        private set => SetField(ref summaryLabel, value);
    }

    public string SelectedDetailTitle => SelectedNavigationKey switch
    {
        "session" => SessionPage.SelectedDetailTitle,
        "devices" => DevicesPage.SelectedDetailTitle,
        "connectivity" => ConnectivityPage.SelectedDetailTitle,
        "transports" => TransportsPage.SelectedDetailTitle,
        "commands" => CommandsPage.SelectedDetailTitle,
        "evidence" => EvidencePage.SelectedDetailTitle,
        "workspaces" => WorkspacesPage.SelectedDetailTitle,
        _ => ReadinessPage.SelectedDetailTitle,
    };

    public string SelectedDetailStatusLine => SelectedNavigationKey switch
    {
        "session" => SessionPage.SelectedDetailStatusLine,
        "devices" => DevicesPage.SelectedDetailStatusLine,
        "connectivity" => ConnectivityPage.SelectedDetailStatusLine,
        "transports" => TransportsPage.SelectedDetailStatusLine,
        "commands" => CommandsPage.SelectedDetailStatusLine,
        "evidence" => EvidencePage.SelectedDetailStatusLine,
        "workspaces" => WorkspacesPage.SelectedDetailStatusLine,
        _ => ReadinessPage.SelectedDetailStatusLine,
    };

    public Brush SelectedDetailBrush => SelectedNavigationKey switch
    {
        "session" => SessionPage.SelectedDetailBrush,
        "devices" => DevicesPage.SelectedDetailBrush,
        "connectivity" => ConnectivityPage.SelectedDetailBrush,
        "transports" => TransportsPage.SelectedDetailBrush,
        "commands" => CommandsPage.SelectedDetailBrush,
        "evidence" => EvidencePage.SelectedDetailBrush,
        "workspaces" => WorkspacesPage.SelectedDetailBrush,
        _ => ReadinessPage.SelectedDetailBrush,
    };

    public string SelectedDetailText => SelectedNavigationKey switch
    {
        "session" => SessionPage.SelectedDetailText,
        "devices" => DevicesPage.SelectedDetailText,
        "connectivity" => ConnectivityPage.SelectedDetailText,
        "transports" => TransportsPage.SelectedDetailText,
        "commands" => CommandsPage.SelectedDetailText,
        "evidence" => EvidencePage.SelectedDetailText,
        "workspaces" => WorkspacesPage.SelectedDetailText,
        _ => ReadinessPage.SelectedDetailText,
    };

    private string SelectedNavigationKey => SelectedNavigationItem?.Key ?? "readiness";

    private async Task RefreshAsync()
    {
        IsBusy = true;
        try
        {
            var report = await readinessService.RefreshAsync(
                Serial,
                UseQuestProfile,
                CheckBroker,
                CancellationToken.None);
            var catalog = await catalogService.RefreshAsync(CancellationToken.None);
            ApplyReport(report);
            ApplyCatalog(catalog);
            await RefreshSessionHistoryListAsync(null, CancellationToken.None);
            SummaryLabel =
                $"{report.Profile}: {report.Summary.Pass} pass, {report.Summary.Warn} warn, " +
                $"{report.Summary.Fail} fail, {report.Summary.Skipped} skipped, " +
                $"{report.Summary.Blocking} blocking. " +
                $"Catalog: {catalog.Summary.Modules} modules, {catalog.Summary.Workspaces} workspaces, " +
                $"{catalog.Summary.Transports} transports, {catalog.Summary.Issues} issues, " +
                $"{EvidenceArtifacts.Count} evidence artifacts.";
        }
        catch (Exception ex)
        {
            reportStatus = "fail";
            catalogStatus = "unknown";
            ReadinessPage.ApplyFailure(ex);
            DevicesPage.ClearRows();
            ConnectivityPage.ClearRows();
            SessionPage.ClearSession();
            TransportsPage.ClearRows();
            CommandsPage.ClearRows();
            EvidencePage.ClearRows();
            WorkspacesPage.ClearRows();
            SummaryLabel = "Companion refresh failed.";
            OnPropertyChanged(nameof(ReportStatusLabel));
            OnPropertyChanged(nameof(ReportStatusBrush));
            OnPropertyChanged(nameof(CatalogStatusLabel));
            OnPropertyChanged(nameof(CatalogStatusBrush));
        }
        finally
        {
            IsBusy = false;
        }
    }

    private async Task RunSessionAsync()
    {
        IsBusy = true;
        try
        {
            var session = await sessionService.RunSessionAsync(
                Serial,
                CheckBroker,
                CancellationToken.None);
            ApplySession(session);
            await RefreshSessionHistoryListAsync(session.ReportPath, CancellationToken.None);
            SummaryLabel =
                $"Session {session.SessionId}: {session.Status}. " +
                $"{session.Summary.PhaseCount} phases, {session.Summary.ArtifactCount} artifacts, " +
                $"{session.Summary.IssueCount} issues.";
        }
        catch (Exception ex)
        {
            SessionPage.ApplyFailure(ex);
            SummaryLabel = "Companion session failed.";
        }
        finally
        {
            IsBusy = false;
        }
    }

    private async Task LoadSessionHistoryAsync()
    {
        IsBusy = true;
        try
        {
            await RefreshSessionHistoryListAsync(null, CancellationToken.None);
            SummaryLabel = $"{SessionHistory.Count} saved sessions loaded.";
        }
        catch (Exception ex)
        {
            SummaryLabel = $"Session history failed: {ex.Message}";
        }
        finally
        {
            IsBusy = false;
        }
    }

    private async Task LoadSelectedSessionAsync()
    {
        if (SelectedSessionHistoryEntry is null)
        {
            return;
        }

        IsBusy = true;
        try
        {
            var session = await sessionService.LoadSessionAsync(
                    SelectedSessionHistoryEntry.ReportPath,
                    CancellationToken.None);
            ApplySession(session);
            SummaryLabel =
                $"Loaded {session.SessionId}: {session.Status}. " +
                $"{session.Summary.PhaseCount} phases, {session.Summary.ArtifactCount} artifacts, " +
                $"{session.Summary.IssueCount} issues.";
        }
        catch (Exception ex)
        {
            SummaryLabel = $"Load session failed: {ex.Message}";
        }
        finally
        {
            IsBusy = false;
        }
    }

    private async Task RunProbeAsync()
    {
        IsBusy = true;
        try
        {
            var execution = await commandService.RunAuthorizedProbeAsync(
                Serial,
                CancellationToken.None);
            ApplyCommandExecution(execution);
            SummaryLabel =
                $"Command {execution.RequestId}: {execution.Status}. " +
                $"{CommandStages.Count} evidence stages returned.";
        }
        catch (Exception ex)
        {
            CommandsPage.ApplyFailure(ex);
            SummaryLabel = "Safe probe failed.";
        }
        finally
        {
            IsBusy = false;
        }
    }

    private async Task PlanFirewallRuleAsync()
    {
        IsBusy = true;
        try
        {
            var report = await connectivityService.PlanFirewallRuleAsync(
                    ConnectivityProgram,
                    ConnectivityProtocol,
                    ConnectivityPort,
                    ConnectivityProfile,
                    ConnectivityRemoteAddress,
                    ConnectivityRuleName,
                    CancellationToken.None);
            ApplyFirewallRuleReport(report);
            SummaryLabel =
                $"Firewall rule plan: {report.Status}. " +
                $"{report.Rule.Name}, {report.Rule.Protocol} {report.Rule.LocalPort}, {report.Rule.RemoteAddress}.";
        }
        catch (Exception ex)
        {
            ApplyConnectivityFailure("host.windows_firewall_rule_plan", ex);
            SummaryLabel = "Firewall rule plan failed.";
        }
        finally
        {
            IsBusy = false;
        }
    }

    private async Task ApplyFirewallRuleAsync()
    {
        IsBusy = true;
        try
        {
            var report = currentFirewallRuleReport
                    ?? await connectivityService.PlanFirewallRuleAsync(
                        ConnectivityProgram,
                        ConnectivityProtocol,
                        ConnectivityPort,
                        ConnectivityProfile,
                        ConnectivityRemoteAddress,
                        ConnectivityRuleName,
                        CancellationToken.None);
            currentFirewallRuleReport = report;
            UpdateFirewallInputsFromReport(report);
            var applied = await connectivityService.ApplyFirewallRuleAsync(report, CancellationToken.None);
            ApplyFirewallRuleReport(applied);
            SummaryLabel =
                $"Firewall rule apply: {connectivityStatus}. " +
                $"{applied.Rule.Name}, {applied.Rule.Protocol} {applied.Rule.LocalPort}.";
        }
        catch (Exception ex)
        {
            ApplyConnectivityFailure("host.windows_firewall_rule_apply", ex);
            SummaryLabel = "Firewall rule apply failed.";
        }
        finally
        {
            IsBusy = false;
        }
    }

    private async Task VerifyFirewallRuleAsync()
    {
        IsBusy = true;
        try
        {
            var report = await connectivityService.VerifyFirewallRuleAsync(
                    ConnectivityProgram,
                    ConnectivityProtocol,
                    ConnectivityPort,
                    ConnectivityProfile,
                    ConnectivityRemoteAddress,
                    ConnectivityRuleName,
                    CancellationToken.None);
            ApplyFirewallRuleReport(report);
            SummaryLabel =
                $"Firewall rule verify: {report.Status}. " +
                $"{report.Rule.Name}, product verified={report.Verification.ProductRuleVerified}.";
        }
        catch (Exception ex)
        {
            ApplyConnectivityFailure("host.windows_firewall_rule_verify", ex);
            SummaryLabel = "Firewall rule verify failed.";
        }
        finally
        {
            IsBusy = false;
        }
    }

    private async Task VerifyConnectivityAsync()
    {
        IsBusy = true;
        try
        {
            if (ConnectivityProtocol == "UDP")
            {
                var run = await connectivityService.RunQcl080StreamCapabilityAsync(
                        Serial,
                        ConnectivityPort,
                        CancellationToken.None);
                ApplyConnectivityCapabilityResult(run);
                SummaryLabel =
                    $"Stream capability {run.Report.RunId}: {run.Descriptor.Status}. " +
                    $"{run.Report.Transport.LocalEndpoint} -> {run.Report.Transport.RemoteEndpoint}.";
            }
            else
            {
                var report = await connectivityService.RunFixedPortProbeAsync(
                        Serial,
                        ConnectivityPort,
                        CancellationToken.None);
                ApplyConnectivityProbeReport(report);
                SummaryLabel =
                    $"Connectivity {report.RunId}: {report.Status}. " +
                    $"{report.Transport.LocalEndpoint} -> {report.Transport.RemoteEndpoint}.";
            }
        }
        catch (Exception ex)
        {
            ApplyConnectivityFailure("connectivity_probe.qcl010", ex);
            SummaryLabel = "Connectivity verification failed.";
        }
        finally
        {
            IsBusy = false;
        }
    }

    private async Task RunConnectivitySuiteAsync()
    {
        IsBusy = true;
        try
        {
            var report = await connectivityService.RunFixtureSuiteAsync(
                    Serial,
                    ConnectivityProgram,
                    ConnectivityProtocol,
                    ConnectivityPort,
                    CancellationToken.None);
            ApplyConnectivitySuiteReport(report);
            SummaryLabel =
                $"Connectivity suite {report.SuiteRunId}: {report.Status}. " +
                $"{report.SlotResults.Count} slots, descriptor {report.SuiteDescriptorPath}.";
        }
        catch (Exception ex)
        {
            ApplyConnectivityFailure("connectivity_probe.run_suite", ex);
            SummaryLabel = "Connectivity suite failed.";
        }
        finally
        {
            IsBusy = false;
        }
    }

    private async Task RunProtocolMatrixAsync()
    {
        IsBusy = true;
        try
        {
            var matrix = await connectivityService.RunProtocolEvidenceMatrixAsync(
                    Serial,
                    ConnectivityProgram,
                    ConnectivityProtocol,
                    ConnectivityPort,
                    CancellationToken.None);
            ApplyProtocolEvidenceMatrix(matrix);
            SummaryLabel =
                $"Protocol matrix {matrix.MatrixId}: {matrix.Status}. " +
                $"{matrix.Rows.Count} capability rows.";
        }
        catch (Exception ex)
        {
            ApplyConnectivityFailure("connectivity_probe.protocol_matrix", ex);
            SummaryLabel = "Protocol matrix failed.";
        }
        finally
        {
            IsBusy = false;
        }
    }

    private async Task RemoveFirewallRuleAsync()
    {
        IsBusy = true;
        try
        {
            var rows = await connectivityService.RemoveFirewallRuleAsync(
                    ConnectivityProgram,
                    ConnectivityRuleName,
                    ConnectivityProtocol,
                    ConnectivityPort,
                    ConnectivityProfile,
                    ConnectivityRemoteAddress,
                    CancellationToken.None);
            ApplyFirewallRuleReport(rows);
            SummaryLabel = $"Firewall rule remove: {connectivityStatus}.";
        }
        catch (Exception ex)
        {
            ApplyConnectivityFailure("host.windows_firewall_rule_remove", ex);
            SummaryLabel = "Firewall rule remove failed.";
        }
        finally
        {
            IsBusy = false;
        }
    }

    private void ApplyReport(ReadinessReport report)
    {
        reportStatus = string.IsNullOrWhiteSpace(report.Status) ? "unknown" : report.Status;
        ReadinessPage.ApplyReport(report);
        DevicesPage.ApplyReadiness(report);
        OnPropertyChanged(nameof(ReportStatusLabel));
        OnPropertyChanged(nameof(ReportStatusBrush));
    }

    private void ApplyCatalog(CompanionCatalog catalog)
    {
        catalogStatus = string.IsNullOrWhiteSpace(catalog.Status) ? "unknown" : catalog.Status;
        TransportsPage.ApplyCatalog(catalog);
        EvidencePage.ApplyCatalog(catalog);
        WorkspacesPage.ApplyCatalog(catalog);
        OnPropertyChanged(nameof(CatalogStatusLabel));
        OnPropertyChanged(nameof(CatalogStatusBrush));
    }

    private void ApplySession(CompanionSessionReport session)
    {
        SessionPage.ApplySession(session, sessionService.ReadArtifactPreview);
        ApplyDeviceLink(sessionService.TryReadDeviceLinkReport(session));
    }

    private void ApplyDeviceLink(DeviceLinkReport? report)
    {
        if (report is null)
        {
            return;
        }

        DevicesPage.ApplyDeviceLink(report);
        TransportsPage.ApplyDeviceLink(report);
    }

    private void ApplyFirewallRuleReport(ConnectivityFirewallRuleReport report)
    {
        currentFirewallRuleReport = report;
        UpdateFirewallInputsFromReport(report);
        ApplyConnectivityRows(ConnectivityRows.ForFirewallPlan(report), report.Status);
    }

    private void UpdateFirewallInputsFromReport(ConnectivityFirewallRuleReport report)
    {
        if (!string.IsNullOrWhiteSpace(report.Rule.Program))
        {
            ConnectivityProgram = report.Rule.Program;
        }
        if (!string.IsNullOrWhiteSpace(report.Rule.Protocol))
        {
            ConnectivityProtocol = report.Rule.Protocol;
        }
        if (report.Rule.LocalPort > 0)
        {
            ConnectivityPort = report.Rule.LocalPort.ToString();
        }
        if (!string.IsNullOrWhiteSpace(report.Rule.Name))
        {
            ConnectivityRuleName = report.Rule.Name;
        }
        if (report.Rule.Profiles.Count > 0)
        {
            ConnectivityProfile = string.Join(",", report.Rule.Profiles);
        }
        if (!string.IsNullOrWhiteSpace(report.Rule.RemoteAddress))
        {
            ConnectivityRemoteAddress = report.Rule.RemoteAddress;
        }
    }

    private void ApplyConnectivityProbeReport(ConnectivityProbeReport report)
    {
        ApplyConnectivityRows(ConnectivityRows.ForProbeReport(report), report.Status);
    }

    private void ApplyConnectivityCapabilityResult(ConnectivityStreamCapabilityRun run)
    {
        ApplyConnectivityRows(ConnectivityRows.ForCapabilityRun(run), run.Descriptor.Status);
    }

    private void ApplyConnectivitySuiteReport(ConnectivitySuiteRunReport report)
    {
        ApplyConnectivityRows(ConnectivityRows.ForSuiteReport(report), report.Status);
    }

    private void ApplyProtocolEvidenceMatrix(ConnectivityProtocolEvidenceMatrix matrix)
    {
        ApplyConnectivityRows(ConnectivityRows.ForProtocolEvidenceMatrix(matrix), matrix.Status);
    }

    private void ApplyConnectivityRows(IReadOnlyList<ConnectivityCheck> rows, string status)
    {
        ConnectivityPage.ApplyRows(rows);
        SetConnectivityStatus(status);
    }

    private void ApplyConnectivityFailure(string checkName, Exception ex)
    {
        ConnectivityPage.ApplyFailure(checkName, ex);
        SetConnectivityStatus("fail");
    }

    private void SetConnectivityStatus(string status)
    {
        connectivityStatus = string.IsNullOrWhiteSpace(status) ? "unknown" : status;
        OnPropertyChanged(nameof(ConnectivityStatusLabel));
        OnPropertyChanged(nameof(ConnectivityStatusBrush));
    }

    private async Task RefreshSessionHistoryListAsync(
        string? selectedReportPath,
        CancellationToken cancellationToken)
    {
        var reports = await sessionService.LoadHistoryAsync(cancellationToken);
        SessionPage.ApplyHistory(reports, selectedReportPath);
    }

    private void ApplyCommandExecution(BridgeCommandExecution execution)
    {
        CommandsPage.ApplyExecution(execution);
    }

    private void ConnectDetailNotifications<TRow>(
        OperatorPageViewModel<TRow> page,
        string selectedPropertyName)
        where TRow : class, IOperatorDetailRow
    {
        page.PropertyChanged += (_, args) =>
        {
            if (args.PropertyName == nameof(OperatorPageViewModel<TRow>.SelectedRow))
            {
                OnPropertyChanged(selectedPropertyName);
            }
            if (OperatorPageViewModel<TRow>.IsSelectedDetailProperty(args.PropertyName))
            {
                OnDetailChanged();
            }
        };
    }

    private void ConnectSessionNotifications()
    {
        SessionPage.PropertyChanged += (_, args) =>
        {
            if (args.PropertyName == nameof(SessionPageViewModel.SelectedHistoryEntry))
            {
                OnPropertyChanged(nameof(SelectedSessionHistoryEntry));
                LoadSelectedSessionCommand.RaiseCanExecuteChanged();
            }
            if (args.PropertyName == nameof(SessionPageViewModel.SelectedPhase))
            {
                OnPropertyChanged(nameof(SelectedSessionPhase));
            }
            if (args.PropertyName == nameof(SessionPageViewModel.SelectedArtifact))
            {
                OnPropertyChanged(nameof(SelectedSessionArtifact));
            }
            if (SessionPageViewModel.IsSelectedDetailProperty(args.PropertyName))
            {
                OnDetailChanged();
            }
        };
    }

    private void OnDetailChanged()
    {
        OnPropertyChanged(nameof(SelectedDetailTitle));
        OnPropertyChanged(nameof(SelectedDetailStatusLine));
        OnPropertyChanged(nameof(SelectedDetailBrush));
        OnPropertyChanged(nameof(SelectedDetailText));
    }

    private static Brush BrushForStatus(string status) => status switch
    {
        "fail" => Brushes.Firebrick,
        "warn" => Brushes.DarkGoldenrod,
        "blocked" => Brushes.Firebrick,
        "rejected" => Brushes.Firebrick,
        "usable_with_warnings" => Brushes.DarkGoldenrod,
        "missing" => Brushes.DarkGoldenrod,
        "unknown" => Brushes.DimGray,
        "planned" => Brushes.DimGray,
        "candidate" => Brushes.DimGray,
        "pass" => Brushes.DarkGreen,
        "usable" => Brushes.DarkGreen,
        "satisfied" => Brushes.DarkGreen,
        _ => Brushes.DimGray,
    };

    private static string DefaultConnectivityRuleName(string portText, string protocol)
    {
        var port = int.TryParse(portText, out var parsed) && parsed > 0 && parsed <= 65535
            ? parsed
            : NormalizeConnectivityProtocol(protocol) == "UDP" ? 18767 : 18766;
        return NormalizeConnectivityProtocol(protocol) == "UDP"
            ? $"Rusty Hostess WPF QCL-080 UDP Freshness {port}"
            : $"Rusty Hostess WPF QCL-010 TCP Echo {port}";
    }

    private static string NormalizeConnectivityProtocol(string protocol) =>
        string.Equals(protocol?.Trim(), "TCP", StringComparison.OrdinalIgnoreCase) ? "TCP" : "UDP";
}
