using System.Text.Json;
using System.Windows.Media;
using HostessCompanion.Wpf.Models;

namespace HostessCompanion.Wpf.ViewModels;

public sealed class SessionPhaseViewModel
{
    private static readonly JsonSerializerOptions DetailJsonOptions = new() { WriteIndented = true };

    public SessionPhaseViewModel(SessionPhase phase)
    {
        PhaseId = phase.PhaseId;
        Title = phase.Title;
        Status = phase.Status;
        Required = phase.Required;
        ActionCount = phase.Summary.ActionCount;
        ArtifactCount = phase.ArtifactRefs.Count;
        IssueCount = phase.Issues.Count;
        Actions = string.Join(
            Environment.NewLine,
            phase.Actions.Select(action =>
                $"{action.Status}  {action.Title}: {action.Evidence}".TrimEnd()));
        ArtifactRefs = phase.ArtifactRefs.Count == 0
            ? "none"
            : string.Join(Environment.NewLine, phase.ArtifactRefs);
        Issues = phase.Issues.Count == 0
            ? "none"
            : string.Join(
                Environment.NewLine,
                phase.Issues.Select(issue => $"{issue.Severity}  {issue.IssueCode}: {issue.Message}"));
        ObservedActions = JsonSerializer.Serialize(phase.Actions, DetailJsonOptions);
    }

    public string PhaseId { get; }

    public string Title { get; }

    public string Status { get; }

    public bool Required { get; }

    public int ActionCount { get; }

    public int ArtifactCount { get; }

    public int IssueCount { get; }

    public string Actions { get; }

    public string ArtifactRefs { get; }

    public string Issues { get; }

    public string ObservedActions { get; }

    public string StatusLine => $"{Status} / {ActionCount} actions / {IssueCount} issues";

    public string DetailText =>
        $"Phase: {PhaseId}{Environment.NewLine}" +
        $"Required: {Required}{Environment.NewLine}" +
        $"Actions:{Environment.NewLine}{Actions}{Environment.NewLine}{Environment.NewLine}" +
        $"Artifacts:{Environment.NewLine}{ArtifactRefs}{Environment.NewLine}{Environment.NewLine}" +
        $"Issues:{Environment.NewLine}{Issues}{Environment.NewLine}{Environment.NewLine}" +
        $"Action details:{Environment.NewLine}{ObservedActions}";

    public Brush StatusBrush => Status switch
    {
        "fail" => Brushes.Firebrick,
        "warn" => Brushes.DarkGoldenrod,
        "skipped" => Brushes.DimGray,
        _ => Brushes.DarkGreen,
    };
}
