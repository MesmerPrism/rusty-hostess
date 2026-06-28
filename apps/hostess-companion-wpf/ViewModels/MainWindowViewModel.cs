using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Runtime.CompilerServices;
using System.Windows.Media;
using HostessCompanion.Wpf.Models;
using HostessCompanion.Wpf.Services;

namespace HostessCompanion.Wpf.ViewModels;

public sealed class MainWindowViewModel : INotifyPropertyChanged
{
    private static readonly HashSet<string> DeviceCheckGroups = ["device", "runtime", "network"];

    private readonly HostessctlReadinessService readinessService;
    private readonly HostessctlCatalogService catalogService;
    private readonly HostessctlCommandService commandService;
    private readonly HostessctlSessionService sessionService;
    private bool isBusy;
    private string reportStatus = "not run";
    private string catalogStatus = "not loaded";
    private string summaryLabel = "No companion reports loaded.";
    private string serial = "";
    private bool useQuestProfile = true;
    private bool checkBroker;
    private CheckViewModel? selectedCheck;
    private CheckViewModel? selectedDeviceCheck;
    private SessionHistoryEntryViewModel? selectedSessionHistoryEntry;
    private SessionPhaseViewModel? selectedSessionPhase;
    private SessionArtifactViewModel? selectedSessionArtifact;
    private TransportViewModel? selectedTransport;
    private CommandStageViewModel? selectedCommandStage;
    private EvidenceArtifactViewModel? selectedEvidenceArtifact;
    private NavigationItemViewModel? selectedNavigationItem;
    private CompanionSessionReport? currentSession;

    public MainWindowViewModel(
        HostessctlReadinessService readinessService,
        HostessctlCatalogService catalogService,
        HostessctlCommandService commandService,
        HostessctlSessionService sessionService)
    {
        this.readinessService = readinessService;
        this.catalogService = catalogService;
        this.commandService = commandService;
        this.sessionService = sessionService;
        NavigationItems.Add(new NavigationItemViewModel("readiness", "Readiness"));
        NavigationItems.Add(new NavigationItemViewModel("session", "Session"));
        NavigationItems.Add(new NavigationItemViewModel("devices", "Devices"));
        NavigationItems.Add(new NavigationItemViewModel("transports", "Transports"));
        NavigationItems.Add(new NavigationItemViewModel("commands", "Commands"));
        NavigationItems.Add(new NavigationItemViewModel("evidence", "Evidence"));
        selectedNavigationItem = NavigationItems[0];
        RefreshCommand = new AsyncRelayCommand(RefreshAsync, () => !IsBusy);
        RunSessionCommand = new AsyncRelayCommand(RunSessionAsync, () => !IsBusy);
        LoadSessionHistoryCommand = new AsyncRelayCommand(LoadSessionHistoryAsync, () => !IsBusy);
        LoadSelectedSessionCommand = new AsyncRelayCommand(
            LoadSelectedSessionAsync,
            () => !IsBusy && SelectedSessionHistoryEntry is not null);
        RunProbeCommand = new AsyncRelayCommand(RunProbeAsync, () => !IsBusy);
    }

    public event PropertyChangedEventHandler? PropertyChanged;

    public ObservableCollection<NavigationItemViewModel> NavigationItems { get; } = [];

    public ObservableCollection<CheckViewModel> Checks { get; } = [];

    public ObservableCollection<CheckViewModel> DeviceChecks { get; } = [];

    public ObservableCollection<SessionHistoryEntryViewModel> SessionHistory { get; } = [];

    public ObservableCollection<SessionPhaseViewModel> SessionPhases { get; } = [];

    public ObservableCollection<SessionArtifactViewModel> SessionArtifacts { get; } = [];

    public ObservableCollection<TransportViewModel> Transports { get; } = [];

    public ObservableCollection<CommandStageViewModel> CommandStages { get; } = [];

    public ObservableCollection<EvidenceArtifactViewModel> EvidenceArtifacts { get; } = [];

    public AsyncRelayCommand RefreshCommand { get; }

    public AsyncRelayCommand RunSessionCommand { get; }

    public AsyncRelayCommand LoadSessionHistoryCommand { get; }

    public AsyncRelayCommand LoadSelectedSessionCommand { get; }

    public AsyncRelayCommand RunProbeCommand { get; }

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
                OnPropertyChanged(nameof(RefreshButtonLabel));
                OnPropertyChanged(nameof(RunSessionButtonLabel));
                OnPropertyChanged(nameof(LoadSessionHistoryButtonLabel));
                OnPropertyChanged(nameof(LoadSelectedSessionButtonLabel));
                OnPropertyChanged(nameof(RunProbeButtonLabel));
            }
        }
    }

    public string RefreshButtonLabel => IsBusy ? "Refreshing" : "Refresh";

    public string RunSessionButtonLabel => IsBusy ? "Running" : "Run session";

    public string LoadSessionHistoryButtonLabel => IsBusy ? "Loading" : "History";

    public string LoadSelectedSessionButtonLabel => IsBusy ? "Loading" : "Load";

    public string RunProbeButtonLabel => IsBusy ? "Running" : "Run safe probe";

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
                OnPropertyChanged(nameof(IsTransportsSelected));
                OnPropertyChanged(nameof(IsCommandsSelected));
                OnPropertyChanged(nameof(IsEvidenceSelected));
                OnDetailChanged();
            }
        }
    }

    public CheckViewModel? SelectedCheck
    {
        get => selectedCheck;
        set
        {
            if (SetField(ref selectedCheck, value))
            {
                OnDetailChanged();
            }
        }
    }

    public CheckViewModel? SelectedDeviceCheck
    {
        get => selectedDeviceCheck;
        set
        {
            if (SetField(ref selectedDeviceCheck, value))
            {
                OnDetailChanged();
            }
        }
    }

    public SessionHistoryEntryViewModel? SelectedSessionHistoryEntry
    {
        get => selectedSessionHistoryEntry;
        set
        {
            if (SetField(ref selectedSessionHistoryEntry, value))
            {
                LoadSelectedSessionCommand.RaiseCanExecuteChanged();
            }
        }
    }

    public SessionPhaseViewModel? SelectedSessionPhase
    {
        get => selectedSessionPhase;
        set
        {
            if (SetField(ref selectedSessionPhase, value))
            {
                PopulateSessionArtifactsForPhase(value);
                OnDetailChanged();
            }
        }
    }

    public SessionArtifactViewModel? SelectedSessionArtifact
    {
        get => selectedSessionArtifact;
        set
        {
            if (SetField(ref selectedSessionArtifact, value))
            {
                OnDetailChanged();
            }
        }
    }

    public TransportViewModel? SelectedTransport
    {
        get => selectedTransport;
        set
        {
            if (SetField(ref selectedTransport, value))
            {
                OnDetailChanged();
            }
        }
    }

    public CommandStageViewModel? SelectedCommandStage
    {
        get => selectedCommandStage;
        set
        {
            if (SetField(ref selectedCommandStage, value))
            {
                OnDetailChanged();
            }
        }
    }

    public EvidenceArtifactViewModel? SelectedEvidenceArtifact
    {
        get => selectedEvidenceArtifact;
        set
        {
            if (SetField(ref selectedEvidenceArtifact, value))
            {
                OnDetailChanged();
            }
        }
    }

    public string PageTitle => SelectedNavigationKey switch
    {
        "session" => "Session",
        "devices" => "Devices",
        "transports" => "Transports",
        "commands" => "Commands",
        "evidence" => "Evidence",
        _ => "Readiness",
    };

    public bool IsReadinessSelected => SelectedNavigationKey == "readiness";

    public bool IsSessionSelected => SelectedNavigationKey == "session";

    public bool IsDevicesSelected => SelectedNavigationKey == "devices";

    public bool IsTransportsSelected => SelectedNavigationKey == "transports";

    public bool IsCommandsSelected => SelectedNavigationKey == "commands";

    public bool IsEvidenceSelected => SelectedNavigationKey == "evidence";

    public string ReportStatusLabel => $"Readiness: {reportStatus}";

    public Brush ReportStatusBrush => BrushForStatus(reportStatus);

    public string CatalogStatusLabel => $"Catalog: {catalogStatus}";

    public Brush CatalogStatusBrush => BrushForStatus(catalogStatus);

    public string SummaryLabel
    {
        get => summaryLabel;
        private set => SetField(ref summaryLabel, value);
    }

    public string SelectedDetailTitle => SelectedNavigationKey switch
    {
        "session" => SelectedSessionArtifact?.Title ?? SelectedSessionPhase?.Title ?? "No session phase selected",
        "devices" => SelectedDeviceCheck?.Title ?? "No device check selected",
        "transports" => SelectedTransport?.Title ?? "No transport selected",
        "commands" => SelectedCommandStage?.Title ?? "No command stage selected",
        "evidence" => SelectedEvidenceArtifact?.Title ?? "No evidence artifact selected",
        _ => SelectedCheck?.Title ?? "No readiness check selected",
    };

    public string SelectedDetailStatusLine => SelectedNavigationKey switch
    {
        "session" => SelectedSessionArtifact?.StatusLine ?? SelectedSessionPhase?.StatusLine ?? "",
        "devices" => SelectedDeviceCheck?.StatusLine ?? "",
        "transports" => SelectedTransport?.StatusLine ?? "",
        "commands" => SelectedCommandStage?.StatusLine ?? "",
        "evidence" => SelectedEvidenceArtifact?.StatusLine ?? "",
        _ => SelectedCheck?.StatusLine ?? "",
    };

    public Brush SelectedDetailBrush => SelectedNavigationKey switch
    {
        "session" => SelectedSessionArtifact?.StatusBrush ?? SelectedSessionPhase?.StatusBrush ?? Brushes.DimGray,
        "devices" => SelectedDeviceCheck?.StatusBrush ?? Brushes.DimGray,
        "transports" => SelectedTransport?.StatusBrush ?? Brushes.DimGray,
        "commands" => SelectedCommandStage?.StatusBrush ?? Brushes.DimGray,
        "evidence" => SelectedEvidenceArtifact?.StatusBrush ?? Brushes.DimGray,
        _ => SelectedCheck?.StatusBrush ?? Brushes.DimGray,
    };

    public string SelectedDetailText => SelectedNavigationKey switch
    {
        "session" => SelectedSessionArtifact?.DetailText ?? SelectedSessionPhase?.DetailText ?? "",
        "devices" => SelectedDeviceCheck?.DetailText ?? "",
        "transports" => SelectedTransport?.DetailText ?? "",
        "commands" => SelectedCommandStage?.DetailText ?? "",
        "evidence" => SelectedEvidenceArtifact?.DetailText ?? "",
        _ => SelectedCheck?.DetailText ?? "",
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
                $"Catalog: {catalog.Summary.Modules} modules, {catalog.Summary.Transports} transports, " +
                $"{EvidenceArtifacts.Count} evidence artifacts.";
        }
        catch (Exception ex)
        {
            reportStatus = "fail";
            catalogStatus = "unknown";
            currentSession = null;
            Checks.Clear();
            DeviceChecks.Clear();
            SessionHistory.Clear();
            SessionPhases.Clear();
            SessionArtifacts.Clear();
            Transports.Clear();
            CommandStages.Clear();
            EvidenceArtifacts.Clear();
            var failure = new CheckViewModel(new ReadinessCheck
            {
                CheckId = "check.wpf.refresh",
                Group = "wpf",
                Title = "Companion refresh",
                Status = "fail",
                Severity = "error",
                Required = true,
                Evidence = ex.Message,
            });
            Checks.Add(failure);
            SelectedCheck = failure;
            SelectedDeviceCheck = null;
            SelectedSessionHistoryEntry = null;
            SelectedSessionPhase = null;
            SelectedSessionArtifact = null;
            SelectedTransport = null;
            SelectedCommandStage = null;
            SelectedEvidenceArtifact = null;
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
            currentSession = null;
            SessionPhases.Clear();
            SessionArtifacts.Clear();
            var failure = new SessionPhaseViewModel(new SessionPhase
            {
                PhaseId = "wpf_session",
                Title = "Companion session",
                Status = "fail",
                Required = true,
                Summary = new SessionSummary
                {
                    ActionCount = 1,
                    Fail = 1,
                    IssueCount = 1,
                },
                Actions =
                [
                    new SessionAction
                    {
                        ActionId = "wpf.session.run",
                        Title = "Run session",
                        Status = "fail",
                        Required = true,
                        Severity = "error",
                        Evidence = ex.Message,
                        IssueCodes = ["hostess.issue.wpf.session_failed"],
                    },
                ],
                Issues =
                [
                    new CommandIssue
                    {
                        IssueCode = "hostess.issue.wpf.session_failed",
                        Severity = "error",
                        Message = ex.Message,
                    },
                ],
            });
            SessionPhases.Add(failure);
            SelectedSessionPhase = failure;
            SelectedSessionArtifact = null;
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
            CommandStages.Clear();
            var failure = new CommandStageViewModel(new CommandStageObservation
            {
                Stage = "wpf_command",
                Status = "fail",
                ObservedAtMs = 0,
                EvidenceRefs = [ex.Message],
                IssueCodes = ["hostess.issue.wpf.command_failed"],
            });
            CommandStages.Add(failure);
            SelectedCommandStage = failure;
            SummaryLabel = "Safe probe failed.";
        }
        finally
        {
            IsBusy = false;
        }
    }

    private void ApplyReport(ReadinessReport report)
    {
        reportStatus = string.IsNullOrWhiteSpace(report.Status) ? "unknown" : report.Status;
        Checks.Clear();
        DeviceChecks.Clear();
        foreach (var check in report.Checks)
        {
            var viewModel = new CheckViewModel(check);
            Checks.Add(viewModel);
            if (DeviceCheckGroups.Contains(viewModel.Group))
            {
                DeviceChecks.Add(viewModel);
            }
        }
        SelectedCheck = Checks.FirstOrDefault();
        SelectedDeviceCheck = DeviceChecks.FirstOrDefault();
        OnPropertyChanged(nameof(ReportStatusLabel));
        OnPropertyChanged(nameof(ReportStatusBrush));
    }

    private void ApplyCatalog(CompanionCatalog catalog)
    {
        catalogStatus = string.IsNullOrWhiteSpace(catalog.Status) ? "unknown" : catalog.Status;
        Transports.Clear();
        foreach (var transport in catalog.Transports)
        {
            Transports.Add(new TransportViewModel(transport));
        }
        EvidenceArtifacts.Clear();
        foreach (var module in catalog.Modules)
        {
            foreach (var artifact in module.EvidenceArtifacts)
            {
                EvidenceArtifacts.Add(new EvidenceArtifactViewModel(module, artifact));
            }
        }
        SelectedTransport = Transports.FirstOrDefault();
        SelectedEvidenceArtifact = EvidenceArtifacts.FirstOrDefault();
        OnPropertyChanged(nameof(CatalogStatusLabel));
        OnPropertyChanged(nameof(CatalogStatusBrush));
    }

    private void ApplySession(CompanionSessionReport session)
    {
        currentSession = session;
        SessionPhases.Clear();
        foreach (var phase in session.Phases)
        {
            SessionPhases.Add(new SessionPhaseViewModel(phase));
        }
        SelectedSessionPhase = SessionPhases.FirstOrDefault();
        if (SelectedSessionPhase is null)
        {
            PopulateSessionArtifactsForPhase(null);
        }
    }

    private async Task RefreshSessionHistoryListAsync(
        string? selectedReportPath,
        CancellationToken cancellationToken)
    {
        var reports = await sessionService.LoadHistoryAsync(cancellationToken);
        SessionHistory.Clear();
        foreach (var report in reports)
        {
            SessionHistory.Add(new SessionHistoryEntryViewModel(report));
        }

        if (!string.IsNullOrWhiteSpace(selectedReportPath))
        {
            SelectedSessionHistoryEntry = SessionHistory.FirstOrDefault(
                entry => string.Equals(
                    entry.ReportPath,
                    selectedReportPath,
                    StringComparison.OrdinalIgnoreCase));
        }
        else
        {
            var currentPath = SelectedSessionHistoryEntry?.ReportPath;
            SelectedSessionHistoryEntry = SessionHistory.FirstOrDefault(
                    entry => string.Equals(
                        entry.ReportPath,
                        currentPath,
                        StringComparison.OrdinalIgnoreCase))
                ?? SessionHistory.FirstOrDefault();
        }
    }

    private void PopulateSessionArtifactsForPhase(SessionPhaseViewModel? phase)
    {
        SessionArtifacts.Clear();
        SelectedSessionArtifact = null;
        if (currentSession is null)
        {
            return;
        }

        var artifactIds = phase?.ArtifactIds.Count > 0
            ? phase.ArtifactIds.ToHashSet(StringComparer.OrdinalIgnoreCase)
            : currentSession.ArtifactRefs.Select(artifact => artifact.ArtifactId)
                .ToHashSet(StringComparer.OrdinalIgnoreCase);
        foreach (var artifact in currentSession.ArtifactRefs.Where(
                     artifact => artifactIds.Contains(artifact.ArtifactId)))
        {
            SessionArtifacts.Add(new SessionArtifactViewModel(
                artifact,
                sessionService.ReadArtifactPreview(artifact)));
        }
    }

    private void ApplyCommandExecution(BridgeCommandExecution execution)
    {
        CommandStages.Clear();
        foreach (var stage in execution.StageObservations)
        {
            CommandStages.Add(new CommandStageViewModel(stage));
        }
        foreach (var issue in execution.Issues)
        {
            CommandStages.Add(new CommandStageViewModel(new CommandStageObservation
            {
                Stage = issue.IssueCode,
                Status = "fail",
                ObservedAtMs = 0,
                EvidenceRefs = [issue.Message],
                IssueCodes = [issue.IssueCode],
            }));
        }
        SelectedCommandStage = CommandStages.FirstOrDefault();
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
        "pass" => Brushes.DarkGreen,
        _ => Brushes.DimGray,
    };

    private bool SetField<T>(ref T field, T value, [CallerMemberName] string propertyName = "")
    {
        if (EqualityComparer<T>.Default.Equals(field, value))
        {
            return false;
        }
        field = value;
        OnPropertyChanged(propertyName);
        return true;
    }

    private void OnPropertyChanged([CallerMemberName] string propertyName = "") =>
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
}
