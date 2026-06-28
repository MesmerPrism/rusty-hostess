using System.Collections.ObjectModel;
using System.Windows.Media;

namespace HostessCompanion.Wpf.ViewModels;

public sealed class SessionPageViewModel : ObservableViewModel
{
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

    private void OnDetailChanged()
    {
        OnPropertyChanged(nameof(SelectedDetailTitle));
        OnPropertyChanged(nameof(SelectedDetailStatusLine));
        OnPropertyChanged(nameof(SelectedDetailBrush));
        OnPropertyChanged(nameof(SelectedDetailText));
    }
}
