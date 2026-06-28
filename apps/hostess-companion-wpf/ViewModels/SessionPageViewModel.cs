using System.Collections.ObjectModel;
using System.Windows.Media;
using HostessCompanion.Wpf.Models;

namespace HostessCompanion.Wpf.ViewModels;

public sealed class SessionPageViewModel : ObservableViewModel
{
    private Func<SessionArtifactRef, string> artifactPreviewReader = _ => "";
    private CompanionSessionReport? currentSession;
    private SessionHistoryEntryViewModel? selectedHistoryEntry;
    private SessionPhaseViewModel? selectedPhase;
    private SessionArtifactViewModel? selectedArtifact;

    public ObservableCollection<SessionHistoryEntryViewModel> History { get; } = [];

    public ObservableCollection<SessionPhaseViewModel> Phases { get; } = [];

    public ObservableCollection<SessionArtifactViewModel> Artifacts { get; } = [];

    public SessionHistoryEntryViewModel? SelectedHistoryEntry
    {
        get => selectedHistoryEntry;
        set => SetField(ref selectedHistoryEntry, value);
    }

    public SessionPhaseViewModel? SelectedPhase
    {
        get => selectedPhase;
        set
        {
            if (SetField(ref selectedPhase, value))
            {
                PopulateArtifactsForPhase(value);
                OnDetailChanged();
            }
        }
    }

    public SessionArtifactViewModel? SelectedArtifact
    {
        get => selectedArtifact;
        set
        {
            if (SetField(ref selectedArtifact, value))
            {
                OnDetailChanged();
            }
        }
    }

    public string SelectedDetailTitle =>
        SelectedArtifact?.Title ?? SelectedPhase?.Title ?? "No session phase selected";

    public string SelectedDetailStatusLine =>
        SelectedArtifact?.StatusLine ?? SelectedPhase?.StatusLine ?? "";

    public Brush SelectedDetailBrush =>
        SelectedArtifact?.StatusBrush ?? SelectedPhase?.StatusBrush ?? Brushes.DimGray;

    public string SelectedDetailText =>
        SelectedArtifact?.DetailText ?? SelectedPhase?.DetailText ?? "";

    public static bool IsSelectedDetailProperty(string? propertyName) =>
        string.IsNullOrEmpty(propertyName)
        || propertyName == nameof(SelectedDetailTitle)
        || propertyName == nameof(SelectedDetailStatusLine)
        || propertyName == nameof(SelectedDetailBrush)
        || propertyName == nameof(SelectedDetailText);

    public void ApplySession(
        CompanionSessionReport session,
        Func<SessionArtifactRef, string> previewReader)
    {
        currentSession = session;
        artifactPreviewReader = previewReader;
        Phases.Clear();
        foreach (var phase in session.Phases)
        {
            Phases.Add(new SessionPhaseViewModel(phase));
        }
        SelectedPhase = Phases.FirstOrDefault();
        if (SelectedPhase is null)
        {
            PopulateArtifactsForPhase(null);
        }
    }

    public void ApplyFailure(Exception ex)
    {
        currentSession = null;
        artifactPreviewReader = _ => "";
        Phases.Clear();
        Artifacts.Clear();
        SelectedArtifact = null;
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
        Phases.Add(failure);
        SelectedPhase = failure;
    }

    public void ApplyHistory(
        IReadOnlyList<CompanionSessionReport> reports,
        string? selectedReportPath)
    {
        var currentPath = SelectedHistoryEntry?.ReportPath;
        History.Clear();
        foreach (var report in reports)
        {
            History.Add(new SessionHistoryEntryViewModel(report));
        }

        if (!string.IsNullOrWhiteSpace(selectedReportPath))
        {
            SelectedHistoryEntry = History.FirstOrDefault(
                entry => string.Equals(
                    entry.ReportPath,
                    selectedReportPath,
                    StringComparison.OrdinalIgnoreCase));
            return;
        }

        SelectedHistoryEntry = History.FirstOrDefault(
                entry => string.Equals(
                    entry.ReportPath,
                    currentPath,
                    StringComparison.OrdinalIgnoreCase))
            ?? History.FirstOrDefault();
    }

    public void ClearSession()
    {
        currentSession = null;
        artifactPreviewReader = _ => "";
        History.Clear();
        Phases.Clear();
        Artifacts.Clear();
        SelectedHistoryEntry = null;
        SelectedPhase = null;
        SelectedArtifact = null;
    }

    private void PopulateArtifactsForPhase(SessionPhaseViewModel? phase)
    {
        Artifacts.Clear();
        SelectedArtifact = null;
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
            Artifacts.Add(new SessionArtifactViewModel(
                artifact,
                artifactPreviewReader(artifact)));
        }
    }

    private void OnDetailChanged()
    {
        OnPropertyChanged(nameof(SelectedDetailTitle));
        OnPropertyChanged(nameof(SelectedDetailStatusLine));
        OnPropertyChanged(nameof(SelectedDetailBrush));
        OnPropertyChanged(nameof(SelectedDetailText));
    }
}
