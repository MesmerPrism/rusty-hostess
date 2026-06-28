using System.Windows.Media;
using HostessCompanion.Wpf.Models;

namespace HostessCompanion.Wpf.ViewModels;

public sealed class CommandStageViewModel : IOperatorDetailRow
{
    public CommandStageViewModel(CommandStageObservation observation)
    {
        Stage = observation.Stage;
        Status = observation.Status;
        ObservedAtMs = observation.ObservedAtMs;
        EvidenceRefs = string.Join(", ", observation.EvidenceRefs);
        IssueCodes = string.Join(", ", observation.IssueCodes);
    }

    public string Stage { get; }

    public string Title => Stage;

    public string Status { get; }

    public long ObservedAtMs { get; }

    public string EvidenceRefs { get; }

    public string IssueCodes { get; }

    public string StatusLine => string.IsNullOrWhiteSpace(IssueCodes)
        ? Status
        : $"{Status} / {IssueCodes}";

    public string DetailText =>
        $"Stage: {Stage}{Environment.NewLine}" +
        $"Status: {Status}{Environment.NewLine}" +
        $"Observed at ms: {ObservedAtMs}{Environment.NewLine}" +
        $"Evidence: {EvidenceRefs}{Environment.NewLine}" +
        $"Issues: {(string.IsNullOrWhiteSpace(IssueCodes) ? "none" : IssueCodes)}";

    public Brush StatusBrush => Status switch
    {
        "fail" => Brushes.Firebrick,
        "warn" => Brushes.DarkGoldenrod,
        _ => Brushes.DarkGreen,
    };
}
